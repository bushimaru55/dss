from __future__ import annotations

from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from analysis_runs.models import AnalysisRun
from analysis_runs.services import run_analysis_to_completion
from datasets.models import Dataset, DatasetStatus, FileType, SheetStructureStatus
from datasets.serializers import detect_file_type
from datasets.services.discovery import discover_and_create_sheets
from datasets.services.preview import clamp_preview_rows, fetch_interpreted_preview, fetch_raw_grid
from datasets.tasks import profile_dataset
from enduser.forms import DatasetUploadForm
from profiling.services import detect_excel_header_row
from suggestions.services import generate_suggestions_for_dataset
from workspaces.models import Workspace


def _parse_header_row_value(val: str | None) -> int | None:
    if val is None:
        return None
    v = str(val).strip()
    if not v or v.lower() == "auto":
        return None
    if v.isdigit() and int(v) >= 1:
        return int(v)
    return None


@login_required
def dashboard(request):
    datasets = Dataset.objects.filter(workspace__owner=request.user).select_related("workspace").prefetch_related("sheets")
    return render(request, "enduser/dashboard.html", {"datasets": datasets})


@login_required
def dataset_new(request):
    if request.method == "POST":
        form = DatasetUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            workspace = form.cleaned_data.get("workspace")
            if not workspace:
                workspace = Workspace.objects.filter(owner=request.user).first()
                if not workspace:
                    workspace = Workspace.objects.create(name="My Workspace", slug=f"ws-{request.user.id}", owner=request.user)

            up_file = form.cleaned_data["file"]
            file_type = detect_file_type(up_file.name)
            if file_type == FileType.UNKNOWN:
                messages.error(request, "CSV または XLSX を選択してください。")
                return render(request, "enduser/dataset_new.html", {"form": form})

            dataset = Dataset.objects.create(
                workspace=workspace,
                uploaded_by=request.user,
                name=form.cleaned_data["name"],
                file=up_file,
                file_type=file_type,
                status=DatasetStatus.UPLOADED,
            )
            discover_and_create_sheets(dataset)
            messages.success(request, "データをアップロードしました。表の見え方を確認してください。")
            return redirect("enduser-dataset-import", dataset_id=dataset.id)
    else:
        form = DatasetUploadForm(user=request.user)

    return render(request, "enduser/dataset_new.html", {"form": form})


@login_required
def dataset_import_confirm(request, dataset_id: int):
    """アップロード直後: シート・ヘッダー行・グリッドを確認してからプロファイルへ。"""
    dataset = get_object_or_404(
        Dataset.objects.select_related("workspace").prefetch_related("sheets"),
        id=dataset_id,
        workspace__owner=request.user,
    )
    sheets = list(dataset.sheets.all().order_by("order", "id"))
    sheet_q = request.GET.get("sheet_id", "").strip()
    if sheet_q.isdigit():
        sheet = dataset.sheets.filter(pk=int(sheet_q)).first()
    else:
        sheet = dataset.sheets.filter(selected=True).first() or (sheets[0] if sheets else None)

    view_mode = (request.GET.get("view") or "interpreted").lower()
    if view_mode not in ("interpreted", "raw"):
        view_mode = "interpreted"
    preview_rows = clamp_preview_rows(int(request.GET.get("preview_rows") or 25))
    header_input = (request.GET.get("header_row") or "").strip()
    header_for_preview = _parse_header_row_value(header_input)

    detected_hint: int | None = None
    if sheet and dataset.file_type == FileType.XLSX:
        detected_hint = detect_excel_header_row(Path(dataset.file.path), sheet.name)
    elif sheet:
        detected_hint = 1

    header_row_effective: int | None = None
    if sheet:
        header_row_effective = (
            header_for_preview if header_for_preview is not None else detected_hint
        )

    interpreted = None
    interpreted_columns: list[str] = []
    interpreted_grid: list[list[str]] = []
    interpreted_table_rows: list[tuple[int, list[str]]] = []
    raw_grid: list[list[str]] | None = None
    raw_col_count = 0
    if sheet:
        if view_mode == "raw":
            raw_grid, raw_col_count = fetch_raw_grid(dataset, sheet, rows=preview_rows)
        else:
            interpreted = fetch_interpreted_preview(
                dataset,
                sheet,
                rows=preview_rows,
                header_row_1based=header_for_preview,
            )
            interpreted_columns = list(interpreted.columns)
            interpreted_grid = [
                [str(row.get(c, "")) for c in interpreted.columns] for row in interpreted.rows
            ]
            hr_for_rows = (
                header_row_effective if header_row_effective is not None else (detected_hint or 1)
            )
            interpreted_table_rows = [
                (hr_for_rows + 1 + i, cells) for i, cells in enumerate(interpreted_grid)
            ]

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "confirm_import":
            sid = request.POST.get("sheet_id", "").strip()
            if not sid.isdigit():
                messages.error(request, "シートを選択してください。")
                return redirect("enduser-dataset-import", dataset_id=dataset.id)
            sh = dataset.sheets.filter(pk=int(sid)).first()
            if not sh:
                messages.error(request, "シートが見つかりません。")
                return redirect("enduser-dataset-import", dataset_id=dataset.id)
            if not request.POST.get("record_grain_ack"):
                messages.error(
                    request,
                    "確認が必要です。表示内容を確認したうえで「表示内容を確認しました」にチェックを入れてください。",
                )
                return redirect("enduser-dataset-import", dataset_id=dataset.id)
            hr = _parse_header_row_value(request.POST.get("header_row"))
            with transaction.atomic():
                dataset.sheets.all().update(selected=False)
                sh.selected = True
                sh.header_row_override = hr
                sh.structure_status = SheetStructureStatus.CONFIRMED
                analysis = dict(sh.analysis or {})
                analysis["record_grain_ack"] = True
                sh.analysis = analysis
                sh.save(update_fields=["selected", "header_row_override", "structure_status", "analysis"])
            profile_dataset(dataset.id)
            generate_suggestions_for_dataset(dataset)
            messages.success(request, "インポート内容を確定し、分析準備を実行しました。")
            return redirect("enduser-dataset-detail", dataset_id=dataset.id)

    return render(
        request,
        "enduser/dataset_import_confirm.html",
        {
            "dataset": dataset,
            "sheets": sheets,
            "sheet": sheet,
            "view_mode": view_mode,
            "preview_rows": preview_rows,
            "header_input": header_input,
            "detected_hint": detected_hint,
            "header_row_effective": header_row_effective,
            "interpreted": interpreted,
            "interpreted_columns": interpreted_columns,
            "interpreted_grid": interpreted_grid,
            "interpreted_table_rows": interpreted_table_rows,
            "raw_grid": raw_grid,
            "raw_col_count": raw_col_count,
        },
    )


@login_required
def dataset_detail(request, dataset_id: int):
    dataset = get_object_or_404(
        Dataset.objects.select_related("workspace").prefetch_related("sheets", "sheets__column_profiles", "suggestions"),
        id=dataset_id,
        workspace__owner=request.user,
    )
    sheet = dataset.sheets.filter(selected=True).first()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "confirm_structure_auto":
            if not sheet:
                messages.error(request, "シートが選択されていません。")
                return redirect("enduser-dataset-detail", dataset_id=dataset.id)
            with transaction.atomic():
                sheet.structure_status = SheetStructureStatus.CONFIRMED
                sheet.header_row_override = None
                sheet.save(update_fields=["structure_status", "header_row_override"])
            profile_dataset(dataset.id)
            generate_suggestions_for_dataset(dataset)
            messages.success(request, "自動検出のヘッダー行で確定し、分析準備を再実行しました。")
            return redirect("enduser-dataset-detail", dataset_id=dataset.id)
        if action == "apply_header_row":
            if not sheet:
                messages.error(request, "シートが選択されていません。")
                return redirect("enduser-dataset-detail", dataset_id=dataset.id)
            raw = (request.POST.get("header_row") or "").strip()
            if not raw.isdigit() or int(raw) < 1:
                messages.error(request, "ヘッダー行は 1 以上の整数で指定してください。")
                return redirect("enduser-dataset-detail", dataset_id=dataset.id)
            with transaction.atomic():
                sheet.header_row_override = int(raw)
                sheet.structure_status = SheetStructureStatus.CONFIRMED
                sheet.save(update_fields=["header_row_override", "structure_status"])
            profile_dataset(dataset.id)
            generate_suggestions_for_dataset(dataset)
            row_n = int(raw)
            messages.success(request, f"行 {row_n} をヘッダーとして適用し、分析準備を再実行しました。")
            return redirect("enduser-dataset-detail", dataset_id=dataset.id)
        if action == "prepare_analysis":
            # MVP: run synchronously from UI to quickly verify candidate generation
            profile_dataset(dataset.id)
            generate_suggestions_for_dataset(dataset)
            messages.success(request, "分析準備が完了し、候補を生成しました。")
            return redirect("enduser-dataset-detail", dataset_id=dataset.id)
        if action == "select_sheet":
            raw = request.POST.get("sheet_id", "")
            if raw.isdigit():
                with transaction.atomic():
                    dataset.sheets.all().update(selected=False)
                    n = dataset.sheets.filter(id=int(raw)).update(selected=True)
                if n:
                    messages.success(request, "シートを切り替えました。必要なら分析準備を再実行してください。")
                else:
                    messages.error(request, "シートが見つかりません。")
            else:
                messages.error(request, "シートを選択してください。")
            return redirect("enduser-dataset-detail", dataset_id=dataset.id)
        if action == "chat":
            if sheet and sheet.structure_needs_user_action():
                messages.error(
                    request,
                    "表の行・列の構造が未確認です。下の「表構造の確認」で自動検出を確定するか、ヘッダー行を指定してから質問してください。",
                )
                return redirect("enduser-dataset-detail", dataset_id=dataset.id)
            question = (request.POST.get("question") or "").strip()
            if not question:
                messages.error(request, "質問を入力してください。")
                return redirect("enduser-dataset-detail", dataset_id=dataset.id)
            run = AnalysisRun.objects.create(dataset=dataset, question=question)
            run_analysis_to_completion(run.id)
            url = reverse("enduser-dataset-detail", kwargs={"dataset_id": dataset.id})
            return redirect(f"{url}?run={run.id}")

    suggestions = dataset.suggestions.all()
    columns = sheet.column_profiles.all().order_by("column_name") if sheet else []

    last_run = None
    run_q = request.GET.get("run", "").strip()
    if run_q.isdigit():
        last_run = AnalysisRun.objects.filter(
            id=int(run_q),
            dataset_id=dataset.id,
            dataset__workspace__owner=request.user,
        ).first()

    return render(
        request,
        "enduser/dataset_detail.html",
        {
            "dataset": dataset,
            "sheet": sheet,
            "columns": columns,
            "suggestions": suggestions,
            "last_run": last_run,
        },
    )
