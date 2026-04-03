from __future__ import annotations

import html
from pathlib import Path

from django.contrib import admin
from django.utils.safestring import mark_safe

from datasets.services.preview import fetch_interpreted_preview

from .models import (
    Dataset,
    DatasetColumnProfile,
    DatasetPreview,
    DatasetProcessingJob,
    DatasetSheet,
    FileType,
)


class DatasetSheetInline(admin.TabularInline):
    model = DatasetSheet
    extra = 0
    fields = (
        "name",
        "order",
        "selected",
        "structure_status",
        "header_row_override",
        "row_count",
        "column_count",
        "preview_ready",
    )
    readonly_fields = ("row_count", "column_count", "preview_ready")


@admin.register(DatasetSheet)
class DatasetSheetAdmin(admin.ModelAdmin):
    list_display = (
        "dataset",
        "name",
        "selected",
        "structure_status",
        "header_row_override",
        "row_count",
        "column_count",
    )
    list_filter = ("structure_status", "selected")
    search_fields = ("name", "dataset__name")
    readonly_fields = ("preview_ready", "row_count", "column_count")


def _build_preview_table_html(columns: list[str], grid_rows: list[list[str]]) -> str:
    th = "".join(f"<th>{html.escape(str(c))}</th>" for c in columns)
    body_parts: list[str] = []
    for row in grid_rows:
        tds = "".join(f"<td>{html.escape(str(c))}</td>" for c in row)
        body_parts.append(f"<tr>{tds}</tr>")
    return (
        '<table style="border-collapse:collapse;font-size:12px;min-width:max-content">'
        f"<thead><tr>{th}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>"
    )


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "file_type", "status", "created_at")
    list_filter = ("status", "file_type")
    inlines = [DatasetSheetInline]
    search_fields = ("name",)
    readonly_fields = (
        "file_download_link",
        "spreadsheet_preview",
        "created_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "workspace",
                    "uploaded_by",
                    "file",
                    "file_type",
                    "status",
                    "error_message",
                )
            },
        ),
        (
            "アップロードファイルの閲覧",
            {
                "description": "ブラウザで開くかダウンロードできます。下の表は選択中シートをヘッダー行設定に従って解釈した先頭行です。",
                "fields": ("file_download_link", "spreadsheet_preview", "created_at"),
            },
        ),
    )

    @admin.display(description="ファイルを開く / ダウンロード")
    def file_download_link(self, obj: Dataset | None) -> str:
        if not obj or not obj.pk or not obj.file:
            return "保存後に表示されます。"
        try:
            url = obj.file.url
        except ValueError:
            return "（ファイル URL を生成できません）"
        name = html.escape(Path(obj.file.name).name)
        return mark_safe(
            f'<p><a href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">'
            f"このファイルを開く（新しいタブ）</a></p>"
            f'<p class="help" style="margin-top:6px">ストレージ上の名前: <code>{name}</code></p>'
        )

    @admin.display(description="表プレビュー（先頭最大40行）")
    def spreadsheet_preview(self, obj: Dataset | None) -> str:
        if not obj or not obj.pk or not obj.file:
            return "保存後に表示されます。"
        path = Path(obj.file.path)
        if not path.is_file():
            return mark_safe('<p class="errornote">ファイルが見つかりません（ストレージを確認してください）。</p>')

        sheet = obj.sheets.filter(selected=True).first() or obj.sheets.order_by("order", "id").first()
        if not sheet:
            return mark_safe("<p>シートがありません。CSV/XLSX の解析後に再度開いてください。</p>")

        if obj.file_type not in (FileType.CSV, FileType.XLSX):
            return "CSV / XLSX 以外は表プレビューに対応していません。"

        try:
            result = fetch_interpreted_preview(
                obj,
                sheet,
                rows=40,
                header_row_1based=sheet.header_row_override,
            )
        except Exception as exc:
            return mark_safe(
                f'<p class="errornote">プレビューを読み込めませんでした: {html.escape(str(exc))}</p>'
            )

        cols = list(result.columns)
        grid = [[str(row.get(c, "")) for c in cols] for row in result.rows]
        table = _build_preview_table_html(cols, grid)
        sheet_label = html.escape(sheet.name)
        ft = "CSV" if obj.file_type == FileType.CSV else "Excel"
        hr_disp = (
            f"{sheet.header_row_override} 行目"
            if sheet.header_row_override
            else "（自動検出）"
        )
        cap = (
            f'<p style="margin:0 0 8px 0"><strong>{ft}</strong> · 対象シート: '
            f"<code>{sheet_label}</code> · ヘッダー行: {html.escape(hr_disp)}</p>"
        )
        wrap = (
            f'<div style="overflow:auto;max-height:480px;border:1px solid #ccc;'
            f'border-radius:4px;padding:8px;background:#fafafa">{cap}{table}</div>'
        )
        return mark_safe(wrap)


@admin.register(DatasetColumnProfile)
class DatasetColumnProfileAdmin(admin.ModelAdmin):
    list_display = ("sheet", "column_name", "inferred_type", "semantic_label")
    search_fields = ("column_name",)


@admin.register(DatasetPreview)
class DatasetPreviewAdmin(admin.ModelAdmin):
    list_display = ("dataset", "sheet", "created_at")


@admin.register(DatasetProcessingJob)
class DatasetProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("dataset", "sheet", "job_type", "status", "updated_at")
    list_filter = ("job_type", "status")
