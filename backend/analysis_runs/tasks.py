from __future__ import annotations

from django_rq import job

from analysis_runs.services import run_analysis_to_completion


@job
def run_analysis_job(run_id: int) -> None:
    run_analysis_to_completion(run_id)
