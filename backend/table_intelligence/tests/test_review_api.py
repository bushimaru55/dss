"""
Review API（session / answers / suppression）の最小テスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_review_api.py
"""

from __future__ import annotations

import uuid

import pytest
from django.urls import reverse

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


@pytest.fixture
def ti_job(user):
    return AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )


@pytest.fixture
def ti_table(ti_job):
    return TableScope.objects.create(
        job=ti_job,
        workspace_id="ws-ti",
    )


@pytest.fixture
def ti_dataset(ti_job, ti_table):
    return NormalizedDataset.objects.create(
        workspace_id="ws-ti",
        job=ti_job,
        table=ti_table,
        schema_version="0.1",
        dataset_payload={"rows": []},
    )


@pytest.fixture
def ti_metadata(ti_dataset):
    return AnalysisMetadata.objects.create(
        dataset=ti_dataset,
        workspace_id="ws-ti",
        review_required=True,
        review_points=[{"id": "p1", "label": "check"}],
        dimensions=[],
        measures=[],
        decision={},
    )


@pytest.mark.django_db
def test_create_review_session_from_metadata_snapshots(auth_client, ti_metadata):
    url = reverse("ti-review-session-create")
    res = auth_client.post(url, {"metadata_id": str(ti_metadata.metadata_id)}, format="json")
    assert res.status_code == 201
    sid = res.data["session_id"]
    assert sid
    assert res.data["metadata_id"] == str(ti_metadata.metadata_id)
    assert res.data["workspace_id"] == "ws-ti"
    assert res.data["state"] == ReviewSessionState.OPEN
    assert res.data["review_required_snapshot"] is True
    assert res.data["review_points_snapshot"] == [{"id": "p1", "label": "check"}]

    session = HumanReviewSession.objects.get(pk=sid)
    assert str(session.session_id) == sid
    assert session.review_required_snapshot == ti_metadata.review_required
    assert session.review_points_snapshot == list(ti_metadata.review_points)


@pytest.mark.django_db
def test_get_review_session(auth_client, ti_metadata, user):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    url = reverse("ti-review-session-detail", kwargs={"session_id": session.session_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["session_id"] == str(session.session_id)
    assert res.data["metadata_id"] == str(ti_metadata.metadata_id)


@pytest.mark.django_db
def test_post_answers_updates_state(auth_client, ti_metadata, user):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    url = reverse("ti-review-session-answers", kwargs={"session_id": session.session_id})
    res = auth_client.post(
        url,
        {
            "answers": [{"question_key": "q1", "answer_value": {"ok": True}}],
            "mark_resolved": True,
            "resolution_grade": "HIGH",
        },
        format="json",
    )
    assert res.status_code == 200
    assert res.data["session"]["state"] == ReviewSessionState.RESOLVED
    assert res.data["session"]["resolution_grade"] == "HIGH"
    assert len(res.data["answers"]) == 1
    assert res.data["answers"][0]["question_key"] == "q1"
    assert res.data["answers"][0]["session_id"] == str(session.session_id)

    session.refresh_from_db()
    assert session.state == ReviewSessionState.RESOLVED


@pytest.mark.django_db
def test_suppression_get_empty_array(auth_client, ti_metadata, user):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    url = reverse("ti-review-session-suppression", kwargs={"session_id": session.session_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data == []


@pytest.mark.django_db
def test_suppression_get_lists_records(auth_client, ti_metadata, user):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    rec = SuppressionRecord.objects.create(
        session=session,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_LIMITED,
        suppression_reason="test",
        suppressed_targets=[{"kind": "cell"}],
    )
    url = reverse("ti-review-session-suppression", kwargs={"session_id": session.session_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert len(res.data) == 1
    assert res.data[0]["id"] == str(rec.id)
    assert res.data[0]["session_id"] == str(session.session_id)
    assert res.data[0]["suppression_level"] == SuppressionLevel.SUGGESTION_LIMITED


@pytest.mark.django_db
def test_review_session_detail_404(auth_client):
    url = reverse("ti-review-session-detail", kwargs={"session_id": uuid.uuid4()})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_create_review_session_metadata_404(auth_client):
    url = reverse("ti-review-session-create")
    res = auth_client.post(
        url,
        {"metadata_id": str(uuid.uuid4())},
        format="json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_post_answers_session_404(auth_client):
    url = reverse("ti-review-session-answers", kwargs={"session_id": uuid.uuid4()})
    res = auth_client.post(
        url,
        {"answers": [{"question_key": "q", "answer_value": {}}]},
        format="json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_review_session_rerun_accepted(auth_client, ti_metadata, user, ti_job):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[{"id": "p1"}],
        created_by=user,
    )
    n_jobs_before = AnalysisJob.objects.count()
    url = reverse("ti-review-session-rerun", kwargs={"session_id": session.session_id})
    res = auth_client.post(url, {}, format="json")
    assert res.status_code == 202
    assert res.data["workspace_id"] == "ws-ti"
    assert res.data["status"] == JobStatus.PENDING
    assert res.data["current_stage"] == "review_upstream_rerun_requested"
    assert "job_id" in res.data

    assert AnalysisJob.objects.count() == n_jobs_before + 1
    job = AnalysisJob.objects.get(pk=res.data["job_id"])
    assert job.requested_by_id == user.id
    pl = job.request_payload
    assert pl["trigger"] == "review_session_rerun"
    assert pl["rerun_from_session_id"] == str(session.session_id)
    assert pl["metadata_id"] == str(ti_metadata.metadata_id)
    assert pl["review_required_snapshot"] is True
    assert pl["review_points_snapshot"] == [{"id": "p1"}]

    session.refresh_from_db()
    assert session.state == ReviewSessionState.OPEN


@pytest.mark.django_db
def test_review_session_rerun_does_not_touch_suppression(auth_client, ti_metadata, user):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    SuppressionRecord.objects.create(
        session=session,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_BLOCKED,
        suppression_reason="keep",
        suppressed_targets=[],
    )
    n_sup = SuppressionRecord.objects.filter(session=session).count()
    url = reverse("ti-review-session-rerun", kwargs={"session_id": session.session_id})
    assert auth_client.post(url, {}, format="json").status_code == 202
    assert SuppressionRecord.objects.filter(session=session).count() == n_sup


@pytest.mark.django_db
def test_review_session_rerun_404(auth_client):
    url = reverse("ti-review-session-rerun", kwargs={"session_id": uuid.uuid4()})
    assert auth_client.post(url, {}, format="json").status_code == 404


@pytest.mark.django_db
def test_review_session_rerun_requires_auth(api_client, ti_metadata, user):
    session = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    url = reverse("ti-review-session-rerun", kwargs={"session_id": session.session_id})
    res = api_client.post(url, {}, format="json")
    assert res.status_code in (401, 403)
