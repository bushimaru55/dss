"""
Suggestion API（013 / 014 / OpenAPI）の MVP テスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_suggestion_api.py
"""

from __future__ import annotations

import uuid

import pytest
from django.urls import reverse

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ArtifactRelation,
    ConfidenceEvaluation,
    HumanReviewSession,
    JobStatus,
    NormalizedDataset,
    ReviewSessionState,
    SuggestionSet,
    SuppressionLevel,
    SuppressionRecord,
    TableScope,
)
from table_intelligence.services import (
    ARTIFACT_TYPE_METADATA,
    LINEAGE_RELATION_JOB_RERUN,
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
        review_points=[],
        dimensions=[{"id": "d1"}],
        measures=[{"id": "m1", "name": "amount"}],
        decision={},
    )


@pytest.fixture
def ti_session(ti_metadata, user):
    return HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )


@pytest.mark.django_db
def test_start_suggestion_run_202_and_get_set(auth_client, ti_metadata, user):
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url_start,
        {"metadata_id": str(ti_metadata.metadata_id)},
        format="json",
    )
    assert res.status_code == 202
    assert res.data["job_id"] is None
    ref = res.data["suggestion_run_ref"]
    assert ref

    sset = SuggestionSet.objects.get(pk=ref)
    assert sset.metadata_id == ti_metadata.metadata_id
    assert sset.created_by_id == user.id
    assert len(sset.analysis_candidates) == 1
    assert sset.analysis_candidates[0]["category"] == "summary_stub"

    url_detail = reverse("ti-suggestion-set-detail", kwargs={"suggestion_run_ref": ref})
    dres = auth_client.get(url_detail)
    assert dres.status_code == 200
    assert str(dres.data["suggestion_run_id"]) == ref
    assert str(dres.data["metadata_id"]) == str(ti_metadata.metadata_id)
    assert dres.data["table_id"] == str(ti_metadata.dataset.table_id)
    assert len(dres.data["analysis_candidates"]) == 1
    assert dres.data["suppression_applied"] == []


@pytest.mark.django_db
def test_suggestion_candidates_endpoint(auth_client, ti_metadata):
    sset = SuggestionSet.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        table=ti_metadata.dataset.table,
        analysis_candidates=[{"candidate_id": "x", "category": "test"}],
        suppression_applied=[],
    )
    url = reverse("ti-suggestion-candidates", kwargs={"suggestion_run_ref": sset.suggestion_run_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["candidates"] == [{"candidate_id": "x", "category": "test"}]
    assert "decision_recommendation" not in res.data


@pytest.mark.django_db
def test_suppression_applied_reads_review_records_not_moving_canonical(
    auth_client, ti_metadata, ti_session, user
):
    SuppressionRecord.objects.create(
        session=ti_session,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_LIMITED,
        suppression_reason="from review",
        suppressed_targets=[{"k": 1}],
    )
    n_sup = SuppressionRecord.objects.count()
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url_start,
        {"metadata_id": str(ti_metadata.metadata_id)},
        format="json",
    )
    assert res.status_code == 202
    sset = SuggestionSet.objects.get(pk=res.data["suggestion_run_ref"])
    assert len(sset.suppression_applied) == 1
    assert sset.suppression_applied[0]["source"] == "review_suppression_record"
    assert sset.suppression_applied[0]["session_id"] == str(ti_session.session_id)
    assert SuppressionRecord.objects.count() == n_sup


@pytest.mark.django_db
def test_start_suggestion_run_explicit_session(auth_client, ti_metadata, ti_session):
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url_start,
        {
            "metadata_id": str(ti_metadata.metadata_id),
            "session_id": str(ti_session.session_id),
        },
        format="json",
    )
    assert res.status_code == 202


@pytest.mark.django_db
def test_start_suggestion_run_wrong_dataset_400(auth_client, ti_metadata):
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url_start,
        {
            "metadata_id": str(ti_metadata.metadata_id),
            "dataset_id": str(uuid.uuid4()),
        },
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_start_suggestion_run_wrong_session_400(auth_client, ti_metadata):
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url_start,
        {
            "metadata_id": str(ti_metadata.metadata_id),
            "session_id": str(uuid.uuid4()),
        },
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_start_suggestion_run_metadata_404(auth_client):
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(
        url_start,
        {"metadata_id": str(uuid.uuid4())},
        format="json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_suggestion_set_detail_404(auth_client):
    url = reverse("ti-suggestion-set-detail", kwargs={"suggestion_run_ref": uuid.uuid4()})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_candidates_include_recommendation_only_011(auth_client, ti_metadata):
    ConfidenceEvaluation.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        confidence_score=0.5,
        decision_recommendation={"level": "caution", "source": "011"},
    )
    sset = SuggestionSet.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        table=ti_metadata.dataset.table,
        analysis_candidates=[],
        suppression_applied=[],
    )
    url = reverse("ti-suggestion-candidates", kwargs={"suggestion_run_ref": sset.suggestion_run_id})
    res = auth_client.get(url, {"include": "recommendation"})
    assert res.status_code == 200
    assert res.data["decision_recommendation"] == {"level": "caution", "source": "011"}
    assert "decision" not in res.data


@pytest.mark.django_db
def test_start_suggestion_run_requires_auth(api_client, ti_metadata):
    url_start = reverse("ti-suggestion-run-start")
    res = api_client.post(
        url_start,
        {"metadata_id": str(ti_metadata.metadata_id)},
        format="json",
    )
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_start_suggestion_run_superseded_metadata_409(auth_client, ti_metadata):
    """artifact_relation 上で旧 metadata -> 新 metadata の SUPERSEDES があるとき 409。"""
    ds = ti_metadata.dataset
    job = ds.job
    table = ds.table
    new_dataset = NormalizedDataset.objects.create(
        workspace_id="ws-ti",
        job=job,
        table=table,
        schema_version="0.1",
        dataset_payload={"rows": []},
    )
    new_meta = AnalysisMetadata.objects.create(
        dataset=new_dataset,
        workspace_id="ws-ti",
        review_required=False,
        review_points=[],
        dimensions=[],
        measures=[{"id": "m1", "name": "amount"}],
        decision={},
    )
    ArtifactRelation.objects.create(
        workspace_id="ws-ti",
        relation_type=LINEAGE_RELATION_JOB_RERUN,
        from_artifact_type=ARTIFACT_TYPE_METADATA,
        from_artifact_id=str(ti_metadata.metadata_id),
        to_artifact_type=ARTIFACT_TYPE_METADATA,
        to_artifact_id=str(new_meta.metadata_id),
        context_job_id=job.job_id,
    )
    url_start = reverse("ti-suggestion-run-start")
    stale = auth_client.post(
        url_start,
        {"metadata_id": str(ti_metadata.metadata_id)},
        format="json",
    )
    assert stale.status_code == 409
    assert stale.data["error_code"] == "TI_CONFLICT"
    assert "detail" in stale.data

    fresh = auth_client.post(
        url_start,
        {"metadata_id": str(new_meta.metadata_id)},
        format="json",
    )
    assert fresh.status_code == 202


@pytest.mark.django_db
def test_measures_empty_yields_no_stub_candidates(auth_client, ti_dataset):
    meta = AnalysisMetadata.objects.create(
        dataset=ti_dataset,
        workspace_id="ws-ti",
        measures=[],
        dimensions=[],
        decision={},
    )
    url_start = reverse("ti-suggestion-run-start")
    res = auth_client.post(url_start, {"metadata_id": str(meta.metadata_id)}, format="json")
    assert res.status_code == 202
    sset = SuggestionSet.objects.get(pk=res.data["suggestion_run_ref"])
    assert sset.analysis_candidates == []
