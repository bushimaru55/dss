from __future__ import annotations

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from datasets.models import Dataset, DatasetStatus, SemanticLabelSource, SheetStructureStatus
from datasets.serializers import (
    DatasetColumnProfileSerializer,
    DatasetCreateSerializer,
    DatasetPreviewSerializer,
    DatasetSheetSerializer,
    DatasetSerializer,
    ImportSettingsSerializer,
    SelectSheetSerializer,
    SemanticMappingSerializer,
)
from datasets.services.preview import (
    clamp_preview_rows,
    fetch_interpreted_preview,
    fetch_raw_grid,
    persist_interpreted_preview,
)
from datasets.tasks import profile_dataset
from semantic_mapping.services import infer_semantic_label
from semantic_mapping.models import SemanticMappingEntry, SemanticMappingRun
from suggestions.serializers import SuggestionSerializer
from suggestions.services import generate_suggestions_for_dataset


class DatasetViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Dataset.objects.select_related("workspace", "uploaded_by").prefetch_related(
        "sheets",
        "sheets__column_profiles",
    )

    def get_queryset(self):
        return self.queryset.filter(workspace__owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return DatasetCreateSerializer
        return DatasetSerializer

    def create(self, request, *args, **kwargs):
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        dataset = create_serializer.save()
        output = DatasetSerializer(dataset, context={"request": request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], url_path="select-sheet")
    def select_sheet(self, request, pk=None):
        dataset = self.get_object()
        ser = SelectSheetSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sheet_id = ser.validated_data["sheet_id"]
        sheet = dataset.sheets.filter(pk=sheet_id).first()
        if not sheet:
            return Response({"detail": "Sheet not found."}, status=status.HTTP_400_BAD_REQUEST)
        dataset.sheets.update(selected=False)
        sheet.selected = True
        sheet.save(update_fields=["selected"])
        dataset.status = DatasetStatus.UPLOADED
        dataset.save(update_fields=["status"])
        out = DatasetSerializer(dataset, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="sheets")
    def sheets(self, request, pk=None):
        dataset = self.get_object()
        return Response({"items": DatasetSheetSerializer(dataset.sheets.all(), many=True).data})

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        dataset = self.get_object()
        sheet = dataset.sheets.filter(selected=True).first()
        sheet_id = request.query_params.get("sheet_id")
        if sheet_id:
            sheet = dataset.sheets.filter(pk=sheet_id).first()
        if not sheet:
            return Response({"detail": "シートが見つかりません。"}, status=status.HTTP_400_BAD_REQUEST)
        rows = clamp_preview_rows(int(request.query_params.get("rows", 20)))
        mode = (request.query_params.get("mode") or "interpreted").lower()
        header_row_raw = (request.query_params.get("header_row") or "").strip()
        header_row_1based: int | None = None
        if header_row_raw.isdigit():
            header_row_1based = int(header_row_raw)

        if mode == "raw":
            grid, _max_cols = fetch_raw_grid(dataset, sheet, rows=rows)
            return Response(
                {
                    "mode": "raw",
                    "sheet_id": sheet.id,
                    "rows": grid,
                    "row_count": len(grid),
                },
                status=status.HTTP_200_OK,
            )

        result = fetch_interpreted_preview(
            dataset,
            sheet,
            rows=rows,
            header_row_1based=header_row_1based,
        )
        preview = persist_interpreted_preview(dataset, sheet, result)
        return Response(DatasetPreviewSerializer(preview).data)

    @action(detail=True, methods=["post"], url_path="import-settings")
    def import_settings(self, request, pk=None):
        """プレビュー確認後にヘッダー行などを保存する。続けて profile を別 API で実行する想定。"""
        dataset = self.get_object()
        ser = ImportSettingsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sheet = dataset.sheets.filter(pk=ser.validated_data["sheet_id"]).first()
        if not sheet:
            return Response({"detail": "シートが見つかりません。"}, status=status.HTTP_400_BAD_REQUEST)
        dataset.sheets.update(selected=False)
        sheet.selected = True
        sheet.header_row_override = ser.validated_data.get("header_row")
        sheet.structure_status = SheetStructureStatus.CONFIRMED
        analysis = dict(sheet.analysis or {})
        if ser.validated_data.get("record_grain_ack"):
            analysis["record_grain_ack"] = True
        sheet.analysis = analysis
        sheet.save(update_fields=["selected", "header_row_override", "structure_status", "analysis"])
        out = DatasetSerializer(dataset, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"], url_path="profile")
    def profile(self, request, pk=None):
        dataset = self.get_object()
        if request.method == "GET":
            sheet = dataset.sheets.filter(selected=True).first()
            if not sheet:
                return Response(
                    {"detail": "シートが選択されていません。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            rows = sheet.column_profiles.all().order_by("column_name")
            return Response(
                {
                    "dataset_id": dataset.id,
                    "sheet": {
                        "id": sheet.id,
                        "name": sheet.name,
                        "row_count": sheet.row_count,
                        "column_count": sheet.column_count,
                        "analysis": sheet.analysis,
                    },
                    "columns": DatasetColumnProfileSerializer(rows, many=True).data,
                }
            )

        if dataset.status == DatasetStatus.PROFILING:
            return Response(
                {"detail": "プロファイル処理中です。"},
                status=status.HTTP_409_CONFLICT,
            )
        sheet = dataset.sheets.filter(selected=True).first()
        if not sheet:
            return Response(
                {"detail": "シートが選択されていません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if dataset.status == DatasetStatus.ERROR:
            dataset.error_message = ""
            dataset.save(update_fields=["error_message"])

        profile_dataset.delay(dataset.id)
        return Response({"enqueued": True, "dataset_id": dataset.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get", "post"], url_path="semantic-mapping")
    def semantic_mapping(self, request, pk=None):
        dataset = self.get_object()
        sheet = dataset.sheets.filter(selected=True).first()
        if not sheet:
            return Response(
                {"detail": "シートが選択されていません。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.method == "GET":
            rows = sheet.column_profiles.all().order_by("column_name")
            return Response({"items": DatasetColumnProfileSerializer(rows, many=True).data})
        ser = SemanticMappingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        by_name = {c.column_name: c for c in sheet.column_profiles.all()}
        user_run = SemanticMappingRun.objects.create(
            dataset=dataset,
            sheet=sheet,
            source=SemanticMappingRun.Source.USER,
        )
        for item in ser.validated_data["columns"]:
            name = item["column_name"]
            label = item["semantic_label"]
            row = by_name.get(name)
            if not row:
                return Response(
                    {"detail": f"列が見つかりません: {name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            row.semantic_label = label
            row.semantic_label_source = SemanticLabelSource.USER
            row.save(update_fields=["semantic_label", "semantic_label_source"])
            SemanticMappingEntry.objects.create(
                run=user_run,
                sheet=sheet,
                column_name=row.column_name,
                semantic_label=label,
                confidence=1.0,
                source=SemanticMappingRun.Source.USER,
            )
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="semantic-mapping/generate")
    def semantic_mapping_generate(self, request, pk=None):
        dataset = self.get_object()
        sheet = dataset.sheets.filter(selected=True).first()
        if not sheet:
            return Response({"detail": "シートが選択されていません。"}, status=status.HTTP_400_BAD_REQUEST)
        count = 0
        for row in sheet.column_profiles.all():
            row.semantic_label = infer_semantic_label(
                row.column_name or row.normalized_name,
                row.inferred_type,
                row.sample_values or [],
            )
            row.semantic_label_source = SemanticLabelSource.AI
            row.save(update_fields=["semantic_label", "semantic_label_source"])
            count += 1
        return Response({"ok": True, "count": count})

    @action(detail=True, methods=["post"], url_path="suggestions/generate")
    def generate_suggestions(self, request, pk=None):
        dataset = self.get_object()
        created = generate_suggestions_for_dataset(dataset)
        return Response(
            {
                "ok": True,
                "count": len(created),
                "items": SuggestionSerializer(created, many=True).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="suggestions")
    def list_suggestions(self, request, pk=None):
        dataset = self.get_object()
        rows = dataset.suggestions.all()
        return Response({"items": SuggestionSerializer(rows, many=True).data})
