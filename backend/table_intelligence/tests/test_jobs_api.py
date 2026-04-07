"""
Jobs API テスト。

SQLite 上で回す場合（ローカルで Postgres が無いとき）::

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_jobs_api.py
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from workspaces.models import Workspace

from table_intelligence.models import AnalysisJob, JobStatus
from table_intelligence.services import execute_mvp_pipeline_for_job


@pytest.mark.django_db
def test_create_job_returns_summary(auth_client):
    url = reverse("ti-table-analysis-job-create")
    res = auth_client.post(
        url,
        data={
            "workspace_id": "ws-test-1",
            "source_type": "upload",
            "source_ref": "s3://bucket/key",
            "request_payload": {"foo": 1},
        },
        format="json",
    )
    assert res.status_code == 202
    assert "job_id" in res.data
    assert res.data["workspace_id"] == "ws-test-1"
    assert res.data["status"] == JobStatus.SUCCEEDED
    assert res.data["current_stage"] == "mvp_pipeline_materialized"
    refs = res.data["artifact_refs"]
    assert refs is not None
    for key in (
        "table_id",
        "dataset_id",
        "metadata_id",
        "evaluation_ref",
        "session_id",
        "suggestion_run_ref",
    ):
        assert key in refs and refs[key]
    assert AnalysisJob.objects.count() == 1


@pytest.mark.django_db
def test_get_job_detail(auth_client, user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-1",
        source_type="t",
        source_ref="r",
        request_payload={"a": 1},
        status=JobStatus.RUNNING,
        current_stage="running",
        requested_by=user,
    )
    url = reverse("ti-table-analysis-job-detail", kwargs={"job_id": job.job_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["job_id"] == str(job.job_id)
    assert res.data["request_payload"] == {"a": 1}
    assert res.data["error_code"] == ""
    assert res.data["requested_by_id"] == user.id


@pytest.mark.django_db
def test_get_job_404(auth_client):
    url = reverse("ti-table-analysis-job-detail", kwargs={"job_id": uuid.uuid4()})
    res = auth_client.get(url)
    assert res.status_code == 404


@pytest.mark.django_db
def test_rerun_creates_new_job(auth_client, user):
    original = AnalysisJob.objects.create(
        workspace_id="ws-1",
        source_type="st",
        source_ref="sr",
        request_payload={"k": "v"},
        status=JobStatus.SUCCEEDED,
        current_stage="done",
        requested_by=user,
    )
    url = reverse("ti-table-analysis-job-rerun", kwargs={"job_id": original.job_id})
    res = auth_client.post(url, data={}, format="json")
    assert res.status_code == 201
    assert res.data["status"] == JobStatus.PENDING
    assert res.data["current_stage"] == "rerun_requested"
    assert AnalysisJob.objects.count() == 2
    new_id = res.data["job_id"]
    new = AnalysisJob.objects.get(pk=new_id)
    assert new.request_payload["k"] == "v"
    assert new.request_payload["lineage"]["relation_type"] == "TI_JOB_RERUN_SUPERSEDES"
    assert new.request_payload["lineage"]["source_job_id"] == str(original.job_id)
    assert new.job_id != original.job_id


@pytest.mark.django_db
def test_rerun_with_payload_override(auth_client, user):
    original = AnalysisJob.objects.create(
        workspace_id="ws-1",
        request_payload={"old": True},
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    url = reverse("ti-table-analysis-job-rerun", kwargs={"job_id": original.job_id})
    res = auth_client.post(url, data={"request_payload": {"new": 2}}, format="json")
    assert res.status_code == 201
    new = AnalysisJob.objects.get(pk=res.data["job_id"])
    assert new.request_payload["new"] == 2
    assert new.request_payload["lineage"]["relation_type"] == "TI_JOB_RERUN_SUPERSEDES"


@pytest.mark.django_db
def test_create_job_validation_400(auth_client):
    url = reverse("ti-table-analysis-job-create")
    res = auth_client.post(url, data={}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_idempotency_key_reuses_job(auth_client):
    url = reverse("ti-table-analysis-job-create")
    body = {
        "workspace_id": "ws-test-1",
        "request_payload": {"idem": True},
    }
    r1 = auth_client.post(url, data=body, format="json", HTTP_IDEMPOTENCY_KEY="key-a")
    assert r1.status_code == 202
    r2 = auth_client.post(url, data=body, format="json", HTTP_IDEMPOTENCY_KEY="key-a")
    assert r2.status_code == 200
    assert r1.data["job_id"] == r2.data["job_id"]
    assert (
        AnalysisJob.objects.filter(
            workspace_id="ws-test-1", idempotency_key="key-a"
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_idempotency_key_scoped_per_workspace(auth_client, user):
    Workspace.objects.create(slug="ws-alt", name="Alt", owner=user)
    url = reverse("ti-table-analysis-job-create")
    r1 = auth_client.post(
        url,
        {"workspace_id": "ws-test-1"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="shared",
    )
    r2 = auth_client.post(
        url,
        {"workspace_id": "ws-alt"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="shared",
    )
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.data["job_id"] != r2.data["job_id"]
    assert AnalysisJob.objects.filter(idempotency_key="shared").count() == 2


@pytest.mark.django_db
@override_settings(TI_TABLE_INTELLIGENCE_PIPELINE_SYNC=False)
@patch("table_intelligence.tasks.run_table_intelligence_mvp_pipeline.delay")
def test_create_job_stays_pending_until_worker(mock_delay, auth_client):
    mock_delay.return_value = None
    url = reverse("ti-table-analysis-job-create")
    res = auth_client.post(
        url,
        {"workspace_id": "ws-test-1", "request_payload": {"async": 1}},
        format="json",
    )
    assert res.status_code == 202
    assert res.data["status"] == JobStatus.PENDING
    mock_delay.assert_called_once()
    jid = uuid.UUID(res.data["job_id"])
    execute_mvp_pipeline_for_job(jid)
    detail = auth_client.get(
        reverse("ti-table-analysis-job-detail", kwargs={"job_id": jid})
    )
    assert detail.status_code == 200
    assert detail.data["status"] == JobStatus.SUCCEEDED
    assert detail.data["artifact_refs"] is not None
    assert detail.data["artifact_refs"].get("dataset_id")
