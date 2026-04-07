"""
012 系最小 ErrorResponse（error_code + detail + errors）の table_intelligence スコープ検証。
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from workspaces.models import Workspace

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    JobStatus,
    NormalizedDataset,
    TableScope,
)


@pytest.fixture
def foreign_workspace_job(db):
    """auth_client の user とは別オーナーの workspace 上のジョブ（越境 404 用）。"""
    u2 = get_user_model().objects.create_user(
        username="foreign_owner",
        password="pw",
        email="f@example.com",
    )
    Workspace.objects.create(name="Foreign", slug="foreign-ws", owner=u2)
    return AnalysisJob.objects.create(
        workspace_id="foreign-ws",
        status=JobStatus.SUCCEEDED,
        requested_by=u2,
    )


@pytest.mark.django_db
def test_not_found_job_includes_error_envelope(auth_client):
    url = reverse("ti-table-analysis-job-detail", kwargs={"job_id": uuid.uuid4()})
    res = auth_client.get(url)
    assert res.status_code == 404
    assert res.data["error_code"] == "TI_NOT_FOUND"
    assert "detail" in res.data


@pytest.mark.django_db
def test_validation_error_job_create_includes_error_envelope(auth_client):
    url = reverse("ti-table-analysis-job-create")
    res = auth_client.post(url, {}, format="json")
    assert res.status_code == 400
    assert res.data["error_code"] == "TI_VALIDATION_ERROR"
    assert res.data["detail"] == "Validation failed."
    assert "errors" in res.data
    assert "workspace_id" in res.data["errors"]


@pytest.mark.django_db
def test_unknown_workspace_returns_404_envelope(auth_client):
    url = reverse("ti-table-analysis-job-create")
    res = auth_client.post(
        url,
        {"workspace_id": "no-such-workspace-slug"},
        format="json",
    )
    assert res.status_code == 404
    assert res.data["error_code"] == "TI_NOT_FOUND"
    assert "detail" in res.data


@pytest.mark.django_db
def test_cross_workspace_resource_404_envelope(auth_client, foreign_workspace_job):
    """workspace 越境は 404 マスク（既存方針）。"""
    url = reverse(
        "ti-table-analysis-job-detail",
        kwargs={"job_id": foreign_workspace_job.job_id},
    )
    res = auth_client.get(url)
    assert res.status_code == 404
    assert res.data["error_code"] == "TI_NOT_FOUND"


@pytest.mark.django_db
def test_unauthenticated_ti_request_has_error_envelope(api_client, user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    scope = TableScope.objects.create(job=job, workspace_id="ws-ti")
    ds = NormalizedDataset.objects.create(
        job=job, table=scope, workspace_id="ws-ti"
    )
    meta = AnalysisMetadata.objects.create(
        dataset=ds,
        workspace_id="ws-ti",
        review_required=False,
        review_points=[],
        dimensions=[],
        measures=[],
        decision={},
    )
    url = reverse("ti-metadata-detail", kwargs={"metadata_id": meta.metadata_id})
    res = api_client.get(url)
    assert res.status_code in (401, 403)
    assert res.data["error_code"] in (
        "TI_AUTHENTICATION_REQUIRED",
        "TI_PERMISSION_DENIED",
    )
    assert "detail" in res.data
