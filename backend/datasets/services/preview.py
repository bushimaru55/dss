"""データセットのプレビュー取得を DRF / エンドユーザー HTML で共通化する。"""

from __future__ import annotations

from pathlib import Path

from datasets.models import Dataset, DatasetPreview, DatasetStatus, FileType
from profiling.services import PandasTabularReader, PreviewResult, read_raw_tabular_grid


def clamp_preview_rows(rows: int) -> int:
    return max(1, min(int(rows), 200))


def fetch_interpreted_preview(
    dataset: Dataset,
    sheet,
    *,
    rows: int,
    header_row_1based: int | None,
) -> PreviewResult:
    reader = PandasTabularReader()
    path = Path(dataset.file.path)
    sheet_name = None if dataset.file_type == FileType.CSV else sheet.name
    n = clamp_preview_rows(rows)
    return reader.read_preview(
        path,
        dataset.file_type,
        sheet_name,
        rows=n,
        header_row_1based=header_row_1based,
    )


def fetch_raw_grid(
    dataset: Dataset,
    sheet,
    *,
    rows: int,
) -> tuple[list[list[str]], int]:
    path = Path(dataset.file.path)
    sheet_name = None if dataset.file_type == FileType.CSV else sheet.name
    n = clamp_preview_rows(rows)
    return read_raw_tabular_grid(path, dataset.file_type, sheet_name, nrows=n)


def persist_interpreted_preview(
    dataset: Dataset,
    sheet,
    result: PreviewResult,
) -> DatasetPreview:
    preview = DatasetPreview.objects.create(
        dataset=dataset,
        sheet=sheet,
        rows=result.rows,
        columns=result.columns,
        summary=result.summary,
    )
    sheet.preview_ready = True
    analysis = dict(sheet.analysis or {})
    if result.summary:
        analysis["preview_summary"] = result.summary
    sheet.analysis = analysis
    sheet.save(update_fields=["preview_ready", "analysis"])
    dataset.status = DatasetStatus.PREVIEWED
    dataset.save(update_fields=["status"])
    return preview
