"""
005 MVP: 004→005 正本サマリ（HumanReviewSession）。解決・確定ロジックは持たない。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_mvp_005_review_state.py
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from table_intelligence.mvp_005_review_state import (
    MVP_005_CANONICAL_REVIEW_SUMMARY_SCHEMA_REF,
    build_mvp_005_canonical_review_summary,
)
from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    HumanReviewSession,
    JobStatus,
    NormalizedDataset,
    ReviewSessionState,
    SuppressionLevel,
    SuppressionRecord,
    TableScope,
)


@pytest.mark.django_db
def test_canonical_summary_reflects_004_intake_unresolved(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    ds = NormalizedDataset.objects.create(
        job=job, table=table, workspace_id="ws-ti", dataset_payload={}
    )
    meta = AnalysisMetadata.objects.create(
        dataset=ds,
        workspace_id="ws-ti",
        review_required=True,
        review_points=[{"point_id": "a", "category": "X"}],
        dimensions=[],
        measures=[],
        decision={},
    )
    session = HumanReviewSession.objects.create(
        metadata=meta,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[{"point_id": "a", "category": "X"}],
        created_by=user,
    )
    s = build_mvp_005_canonical_review_summary(session)
    assert s["schema_ref"] == MVP_005_CANONICAL_REVIEW_SUMMARY_SCHEMA_REF
    assert s["semantic_lock_in"] is False
    assert s["from_004_review_required_snapshot"] is True
    assert s["from_004_review_point_count_at_intake"] == 1
    assert s["resolution_status"] == "PENDING"
    assert s["unresolved_work_present"] is True
    assert s["uncertainty_intake_present"] is True
    assert s["suppression_status"] == "NONE"
    assert s["suppression_record_count"] == 0


@pytest.mark.django_db
def test_canonical_summary_suppression_present_without_interpretation(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti", status=JobStatus.SUCCEEDED, requested_by=user
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    ds = NormalizedDataset.objects.create(
        job=job, table=table, workspace_id="ws-ti", dataset_payload={}
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
    session = HumanReviewSession.objects.create(
        metadata=meta,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    SuppressionRecord.objects.create(
        session=session,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_LIMITED,
        suppression_reason="mvp",
    )
    s = build_mvp_005_canonical_review_summary(session)
    assert s["suppression_status"] == "PRESENT"
    assert s["suppression_record_count"] == 1


@pytest.mark.django_db
def test_canonical_summary_resolved_does_not_imply_meaning_lock(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti", status=JobStatus.SUCCEEDED, requested_by=user
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    ds = NormalizedDataset.objects.create(
        job=job, table=table, workspace_id="ws-ti", dataset_payload={}
    )
    meta = AnalysisMetadata.objects.create(
        dataset=ds,
        workspace_id="ws-ti",
        review_required=True,
        review_points=[{"id": "p"}],
        dimensions=[],
        measures=[],
        decision={},
    )
    session = HumanReviewSession.objects.create(
        metadata=meta,
        workspace_id="ws-ti",
        state=ReviewSessionState.RESOLVED,
        review_required_snapshot=True,
        review_points_snapshot=[{"id": "p"}],
        resolution_grade="mvp-test-grade",
        created_by=user,
    )
    s = build_mvp_005_canonical_review_summary(session)
    assert s["resolution_status"] == "RESOLVED"
    assert s["unresolved_work_present"] is False
    assert s["resolution_grade"] == "mvp-test-grade"
    assert s["semantic_lock_in"] is False


@pytest.mark.django_db
def test_create_session_api_exposes_005_summary(auth_client, user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti", status=JobStatus.SUCCEEDED, requested_by=user
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    ds = NormalizedDataset.objects.create(
        job=job, table=table, workspace_id="ws-ti", dataset_payload={}
    )
    meta = AnalysisMetadata.objects.create(
        dataset=ds,
        workspace_id="ws-ti",
        review_required=True,
        review_points=[{"point_id": "from-004"}],
        dimensions=[],
        measures=[],
        decision={},
    )
    url = reverse("ti-review-session-create")
    res = auth_client.post(url, {"metadata_id": str(meta.metadata_id)}, format="json")
    assert res.status_code == 201
    summ = res.data["mvp_005_canonical_summary"]
    assert summ["schema_ref"] == MVP_005_CANONICAL_REVIEW_SUMMARY_SCHEMA_REF
    assert summ["from_004_review_point_count_at_intake"] == 1
    assert summ["uncertainty_intake_present"] is True
    assert summ["semantic_lock_in"] is False
