"""
MVP 表解析パイプラインの投入口。

``TI_TABLE_INTELLIGENCE_PIPELINE_SYNC`` が真のときは Redis なしでインライン実行（テスト用）。
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.http import HttpRequest

from table_intelligence.services import execute_mvp_pipeline_for_job


def parse_idempotency_key(request: HttpRequest) -> str | None:
    raw = (request.META.get("HTTP_IDEMPOTENCY_KEY") or "").strip()
    if not raw:
        return None
    return raw[:128]


def schedule_mvp_pipeline(job_id: uuid.UUID) -> None:
    if getattr(settings, "TI_TABLE_INTELLIGENCE_PIPELINE_SYNC", False):
        execute_mvp_pipeline_for_job(job_id)
        return
    from table_intelligence.tasks import run_table_intelligence_mvp_pipeline

    run_table_intelligence_mvp_pipeline.delay(str(job_id))
