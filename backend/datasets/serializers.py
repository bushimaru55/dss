from __future__ import annotations

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from datasets.models import (
    Dataset,
    DatasetColumnProfile,
    DatasetFile,
    DatasetPreview,
    DatasetProcessingJob,
    DatasetSheet,
    DatasetStatus,
    FileType,
    SemanticLabel,
)
from datasets.services.discovery import discover_and_create_sheets
from workspaces.models import Workspace


def detect_file_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return FileType.CSV
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        return FileType.XLSX
    return FileType.UNKNOWN


class DatasetSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetSheet
        fields = (
            "id",
            "name",
            "order",
            "selected",
            "row_count",
            "column_count",
            "preview_ready",
            "analysis",
            "structure_status",
            "header_row_override",
        )
        read_only_fields = fields


class DatasetColumnProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetColumnProfile
        fields = (
            "id",
            "column_name",
            "normalized_name",
            "inferred_type",
            "null_ratio",
            "unique_ratio",
            "sample_values",
            "warnings",
            "semantic_label",
            "semantic_label_source",
        )
        read_only_fields = fields


class DatasetPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetPreview
        fields = ("id", "dataset", "sheet", "columns", "rows", "summary", "created_at")
        read_only_fields = fields


class DatasetProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetProcessingJob
        fields = (
            "id",
            "dataset",
            "sheet",
            "job_type",
            "status",
            "payload",
            "result",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DatasetSerializer(serializers.ModelSerializer):
    sheets = DatasetSheetSerializer(many=True, read_only=True)
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    file_record = serializers.SerializerMethodField()

    def get_file_record(self, obj):
        if not hasattr(obj, "file_record"):
            return None
        rec = obj.file_record
        return {
            "original_name": rec.original_name,
            "mime_type": rec.mime_type,
            "size_bytes": rec.size_bytes,
            "storage_path": rec.storage_path,
        }

    class Meta:
        model = Dataset
        fields = (
            "id",
            "workspace",
            "uploaded_by",
            "uploaded_by_username",
            "name",
            "file",
            "file_type",
            "status",
            "error_message",
            "created_at",
            "sheets",
            "file_record",
        )
        read_only_fields = (
            "id",
            "uploaded_by",
            "uploaded_by_username",
            "file_type",
            "status",
            "error_message",
            "created_at",
            "sheets",
            "file_record",
        )


class DatasetCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Dataset
        fields = ("name", "workspace", "file")

    def validate_workspace(self, value: Workspace) -> Workspace:
        request = self.context["request"]
        if value.owner_id != request.user.id:
            raise serializers.ValidationError("このワークスペースへはアップロードできません。")
        return value

    def validate_file(self, value: UploadedFile) -> UploadedFile:
        ft = detect_file_type(value.name)
        if ft == FileType.UNKNOWN:
            raise serializers.ValidationError("CSV または XLSX のみ対応しています。")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        file = validated_data.pop("file")
        ft = detect_file_type(file.name)
        dataset = Dataset.objects.create(
            **validated_data,
            uploaded_by=request.user,
            file=file,
            file_type=ft,
            status=DatasetStatus.UPLOADED,
        )
        DatasetFile.objects.create(
            dataset=dataset,
            original_name=file.name,
            mime_type=getattr(file, "content_type", "") or "",
            size_bytes=getattr(file, "size", 0) or 0,
            storage_path=dataset.file.name,
        )
        discover_and_create_sheets(dataset)
        return dataset


class SelectSheetSerializer(serializers.Serializer):
    sheet_id = serializers.IntegerField(required=True)


class ImportSettingsSerializer(serializers.Serializer):
    """インポート確認でシート・ヘッダー行・レコード粒度の同意を保存する（プロファイル前）。"""

    sheet_id = serializers.IntegerField(required=True)
    header_row = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    record_grain_ack = serializers.BooleanField(required=False, default=False)


class SemanticMappingItemSerializer(serializers.Serializer):
    column_name = serializers.CharField(max_length=512)
    semantic_label = serializers.ChoiceField(choices=SemanticLabel.choices)


class SemanticMappingSerializer(serializers.Serializer):
    columns = SemanticMappingItemSerializer(many=True)
