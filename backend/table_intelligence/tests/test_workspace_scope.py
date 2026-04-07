"""
workspace スコープ: 他 slug（workspace_id）越境は 404。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_workspace_scope.py
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ConfidenceEvaluation,
    HumanReviewSession,
    JobStatus,
    NormalizedDataset,
    SuggestionSet,
    TableScope,
)


@pytest.fixture
def user2(db):
    User = get_user_model()
    return User.objects.create_user(
        username="other",
        password="other",
        email="other@example.com",
    )


@pytest.fixture
def auth_client_user2(api_client, user2):
    api_client.force_authenticate(user=user2)
    return api_client


@pytest.fixture
def alien_job(user2):
    """user2 のみがアクセス可能な workspace（slug は TI に載せない）。"""
    from workspaces.models import Workspace

    Workspace.objects.create(name="Alien", slug="alien-ws", owner=user2)
    return AnalysisJob.objects.create(
        workspace_id="alien-ws",
        status=JobStatus.SUCCEEDED,
        requested_by=user2,
    )


@pytest.fixture
def alien_chain(user2, alien_job):
    scope = TableScope.objects.create(job=alien_job, workspace_id="alien-ws")
    table_id = scope.table_id
    ds = NormalizedDataset.objects.create(
        job=alien_job,
        table=scope,
        workspace_id="alien-ws",
    )
    meta = AnalysisMetadata.objects.create(
        dataset=ds,
        workspace_id="alien-ws",
        review_required=True,
        review_points=[],
        dimensions=[],
        measures=[{"id": "m"}],
        decision={},
    )
    session = HumanReviewSession.objects.create(
        metadata=meta,
        workspace_id="alien-ws",
        review_required_snapshot=True,
        review_points_snapshot=[],
    )
    sset = SuggestionSet.objects.create(
        metadata=meta,
        workspace_id="alien-ws",
        table=scope,
        analysis_candidates=[{"candidate_id": "x"}],
        suppression_applied=[],
    )
    ev = ConfidenceEvaluation.objects.create(
        metadata=meta,
        workspace_id="alien-ws",
        confidence_score=0.5,
        decision_recommendation={"source": "011"},
    )
    return {
        "job": alien_job,
        "table_id": table_id,
        "dataset_id": ds.dataset_id,
        "metadata_id": meta.metadata_id,
        "session_id": session.session_id,
        "suggestion_run_ref": sset.suggestion_run_id,
        "evaluation_ref": ev.evaluation_id,
    }


@pytest.mark.django_db
def test_get_job_cross_workspace_404(auth_client, alien_job):
    url = reverse("ti-table-analysis-job-detail", kwargs={"job_id": alien_job.job_id})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_post_job_unknown_workspace_404(auth_client):
    url = reverse("ti-table-analysis-job-create")
    res = auth_client.post(
        url,
        {"workspace_id": "no-such-workspace-slug"},
        format="json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_get_dataset_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-dataset-detail", kwargs={"dataset_id": alien_chain["dataset_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_metadata_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-metadata-detail", kwargs={"metadata_id": alien_chain["metadata_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_review_session_create_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-review-session-create")
    res = auth_client.post(
        url,
        {"metadata_id": str(alien_chain["metadata_id"])},
        format="json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_review_session_get_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-review-session-detail", kwargs={"session_id": alien_chain["session_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_evaluation_cross_workspace_404(auth_client, alien_chain):
    url = reverse(
        "ti-evaluation-detail",
        kwargs={"evaluation_ref": alien_chain["evaluation_ref"]},
    )
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_post_suggestion_run_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url,
        {"metadata_id": str(alien_chain["metadata_id"])},
        format="json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_suggestion_get_cross_workspace_404(auth_client, alien_chain):
    url = reverse(
        "ti-suggestion-set-detail",
        kwargs={"suggestion_run_ref": alien_chain["suggestion_run_ref"]},
    )
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_job_rerun_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-table-analysis-job-rerun", kwargs={"job_id": alien_chain["job"].job_id})
    assert auth_client.post(url, {}, format="json").status_code == 404


@pytest.mark.django_db
def test_review_answers_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-review-session-answers", kwargs={"session_id": alien_chain["session_id"]})
    assert (
        auth_client.post(
            url,
            {"answers": [{"question_key": "q", "answer_value": {}}]},
            format="json",
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_review_rerun_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-review-session-rerun", kwargs={"session_id": alien_chain["session_id"]})
    assert auth_client.post(url, {}, format="json").status_code == 404


@pytest.mark.django_db
def test_suppression_get_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-review-session-suppression", kwargs={"session_id": alien_chain["session_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_suggestion_candidates_cross_workspace_404(auth_client, alien_chain):
    url = reverse(
        "ti-suggestion-candidates",
        kwargs={"suggestion_run_ref": alien_chain["suggestion_run_ref"]},
    )
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_owner_can_access_own_alien_data(auth_client_user2, alien_chain):
    job = alien_chain["job"]
    url = reverse("ti-table-analysis-job-detail", kwargs={"job_id": job.job_id})
    assert auth_client_user2.get(url).status_code == 200


@pytest.mark.django_db
def test_get_table_summary_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-table-summary", kwargs={"table_id": alien_chain["table_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_table_artifacts_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-table-artifacts", kwargs={"table_id": alien_chain["table_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_table_decision_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-table-decision", kwargs={"table_id": alien_chain["table_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_table_read_artifact_cross_workspace_404(auth_client, alien_chain):
    url = reverse("ti-table-read-artifact", kwargs={"table_id": alien_chain["table_id"]})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_metadata_review_points_cross_workspace_404(auth_client, alien_chain):
    url = reverse(
        "ti-metadata-review-points",
        kwargs={"metadata_id": alien_chain["metadata_id"]},
    )
    assert auth_client.get(url).status_code == 404
