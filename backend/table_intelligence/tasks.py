"""django-rq タスク（表解析 MVP パイプライン）。"""

from __future__ import annotations

import uuid

from django_rq import job

from table_intelligence.services import execute_mvp_pipeline_for_job


@job
def run_table_intelligence_mvp_pipeline(job_id: str) -> None:
    execute_mvp_pipeline_for_job(uuid.UUID(job_id))
