"""
GET /tables/* および GET /metadata/<id>/review-points/ の MVP テスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_tables_api.py
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ConfidenceEvaluation,
    HumanReviewSession,
    JobStatus,
    JudgmentDecision,
    JudgmentResult,
    NormalizedDataset,
    SuggestionSet,
    TableReadArtifact,
    TableScope,
    TI_TABLE_UNKNOWN,
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
        sheet_name="S1",
        row_min=0,
        col_min=0,
        row_max=2,
        col_max=3,
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
        review_points=[{"id": "rp1", "severity": "warn"}],
        dimensions=[],
        measures=[],
        decision={"block": "004"},
    )


@pytest.fixture
def ti_session(ti_metadata):
    return HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        review_required_snapshot=True,
        review_points_snapshot=[],
    )


@pytest.fixture
def ti_suggestion(ti_metadata, ti_table):
    return SuggestionSet.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        table=ti_table,
        analysis_candidates=[],
        suppression_applied=[],
    )


@pytest.fixture
def ti_evaluation(ti_metadata):
    return ConfidenceEvaluation.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        confidence_score=0.5,
        decision_recommendation={"source": "011"},
    )


@pytest.mark.django_db
def test_table_summary_and_refs(auth_client, ti_table, ti_dataset, ti_metadata):
    url = reverse("ti-table-summary", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["table_id"] == str(ti_table.table_id)
    refs = res.data["refs"]
    assert refs["dataset_id"] == str(ti_dataset.dataset_id)
    assert refs["metadata_id"] == str(ti_metadata.metadata_id)
    assert refs["read_artifact_id"] == ""
    assert refs["judgment_id"] == ""
    assert "read_artifact_id" in refs
    assert "judgment_id" in refs
    assert all(isinstance(v, str) for v in refs.values())
    assert all(v is not None for v in refs.values())


@pytest.mark.django_db
def test_table_summary_refs_includes_latest_read_artifact_and_judgment_ids(
    auth_client, ti_table, ti_dataset, ti_metadata, ti_job
):
    tra = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        cells={},
        merges=[],
        parse_warnings=[],
    )
    jr = JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        decision=JudgmentDecision.NEEDS_REVIEW,
        taxonomy_code=TI_TABLE_UNKNOWN,
        evidence=[],
    )
    url = reverse("ti-table-summary", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    refs = res.data["refs"]
    assert refs["read_artifact_id"] == str(tra.artifact_id)
    assert refs["judgment_id"] == str(jr.judgment_id)
    assert refs["metadata_id"] == str(ti_metadata.metadata_id)
    assert all(isinstance(v, str) for v in refs.values())
    assert all(v is not None for v in refs.values())


@pytest.mark.django_db
def test_table_summary_refs_no_dataset_still_exposes_read_artifact_id(
    auth_client, ti_table, ti_job
):
    """データセット列が無くても table 直結 latest の導線キーは refs に載る（Phase 1）。"""
    tra = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        cells={},
        merges=[],
        parse_warnings=[],
    )
    url = reverse("ti-table-summary", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    refs = res.data["refs"]
    assert refs["dataset_id"] == ""
    assert refs["metadata_id"] == ""
    assert refs["read_artifact_id"] == str(tra.artifact_id)
    assert refs["judgment_id"] == ""
    assert all(isinstance(v, str) for v in refs.values())
    assert all(v is not None for v in refs.values())


@pytest.mark.django_db
def test_table_summary_refs_read_artifact_only(
    auth_client, ti_table, ti_dataset, ti_metadata, ti_job
):
    tra = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        cells={},
        merges=[],
        parse_warnings=[],
    )
    url = reverse("ti-table-summary", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    refs = res.data["refs"]
    assert refs["read_artifact_id"] == str(tra.artifact_id)
    assert refs["judgment_id"] == ""


@pytest.mark.django_db
def test_table_summary_refs_judgment_only(
    auth_client, ti_table, ti_dataset, ti_metadata, ti_job
):
    jr = JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        decision=JudgmentDecision.NEEDS_REVIEW,
        taxonomy_code=TI_TABLE_UNKNOWN,
        evidence=[],
    )
    url = reverse("ti-table-summary", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    refs = res.data["refs"]
    assert refs["read_artifact_id"] == ""
    assert refs["judgment_id"] == str(jr.judgment_id)


@pytest.mark.django_db
def test_table_read_artifact_from_db(auth_client, ti_table, ti_job):
    row = TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        cells={"R0C0": {"raw_display": "x", "r": 0, "c": 0}},
        merges=[],
        parse_warnings=[],
    )
    url = reverse("ti-table-read-artifact", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["table_id"] == str(ti_table.table_id)
    assert res.data["artifact_id"] == str(row.artifact_id)
    assert res.data["merges"] == []
    assert res.data["parse_warnings"] == []
    assert res.data["cells"]["R0C0"]["raw_display"] == "x"


@pytest.mark.django_db
def test_table_read_artifact_404_without_row(auth_client, ti_table):
    url = reverse("ti-table-read-artifact", kwargs={"table_id": ti_table.table_id})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_table_decision_from_db_no_011(auth_client, ti_table, ti_job):
    JudgmentResult.objects.create(
        workspace_id="ws-ti",
        table=ti_table,
        job=ti_job,
        decision=JudgmentDecision.NEEDS_REVIEW,
        taxonomy_code=TI_TABLE_UNKNOWN,
        evidence=[
            {
                "rule_id": "J2-TEST",
                "conclusion": "c",
                "message": "m",
                "targets": [],
            }
        ],
    )
    url = reverse("ti-table-decision", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["table_id"] == str(ti_table.table_id)
    assert res.data["decision"] == "NEEDS_REVIEW"
    assert res.data["taxonomy_code"] == TI_TABLE_UNKNOWN
    assert len(res.data["evidence"]) >= 1
    assert "decision_recommendation" not in res.data


@pytest.mark.django_db
def test_table_decision_404_without_judgment_row(auth_client, ti_table):
    url = reverse("ti-table-decision", kwargs={"table_id": ti_table.table_id})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_table_artifacts_bundles(
    auth_client,
    ti_table,
    ti_dataset,
    ti_metadata,
    ti_session,
    ti_suggestion,
    ti_evaluation,
):
    url = reverse("ti-table-artifacts", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert len(res.data["items"]) == 1
    item = res.data["items"][0]
    assert item["table_id"] == str(ti_table.table_id)
    assert item["dataset_id"] == str(ti_dataset.dataset_id)
    assert item["metadata_id"] == str(ti_metadata.metadata_id)
    assert item["session_id"] == str(ti_session.session_id)
    assert item["evaluation_ref"] == str(ti_evaluation.evaluation_id)
    assert item["suggestion_run_ref"] == str(ti_suggestion.suggestion_run_id)


@pytest.mark.django_db
def test_table_artifacts_empty_when_no_dataset(auth_client, ti_table):
    url = reverse("ti-table-artifacts", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["items"] == []


@pytest.mark.django_db
def test_metadata_review_points(auth_client, ti_metadata, ti_dataset):
    url = reverse(
        "ti-metadata-review-points",
        kwargs={"metadata_id": ti_metadata.metadata_id},
    )
    expected_points = [{"id": "rp1", "severity": "warn"}]
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["metadata_id"] == str(ti_metadata.metadata_id)
    assert res.data["table_id"] == str(ti_dataset.table_id)
    assert isinstance(res.data["table_id"], str)
    assert res.data["review_required"] is True
    assert isinstance(res.data["review_required"], bool)
    assert res.data["dataset_id"] == str(ti_dataset.dataset_id)
    assert isinstance(res.data["dataset_id"], str)
    assert res.data["review_points"] == expected_points
    assert "review_required" in res.data
    assert "dataset_id" in res.data
    assert "review_points_count" in res.data
    assert isinstance(res.data["review_points_count"], int)
    assert res.data["review_points_count"] == len(res.data["review_points"])
    assert res.data["review_points_count"] == 1


@pytest.mark.django_db
def test_metadata_review_points_review_required_false(auth_client, ti_dataset):
    meta = AnalysisMetadata.objects.create(
        dataset=ti_dataset,
        workspace_id="ws-ti",
        review_required=False,
        review_points=[{"id": "rp1", "severity": "warn"}],
        dimensions=[],
        measures=[],
        decision={},
    )
    url = reverse(
        "ti-metadata-review-points",
        kwargs={"metadata_id": meta.metadata_id},
    )
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["review_required"] is False
    assert isinstance(res.data["review_required"], bool)
    assert res.data["dataset_id"] == str(ti_dataset.dataset_id)
    assert res.data["table_id"] == str(ti_dataset.table_id)
    assert isinstance(res.data["table_id"], str)
    assert res.data["review_points"] == [{"id": "rp1", "severity": "warn"}]
    assert res.data["review_points_count"] == len(res.data["review_points"]) == 1


@pytest.mark.django_db
def test_metadata_review_points_count_zero_when_empty(auth_client, ti_dataset):
    meta = AnalysisMetadata.objects.create(
        dataset=ti_dataset,
        workspace_id="ws-ti",
        review_required=False,
        review_points=[],
        dimensions=[],
        measures=[],
        decision={},
    )
    url = reverse(
        "ti-metadata-review-points",
        kwargs={"metadata_id": meta.metadata_id},
    )
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["review_points"] == []
    assert res.data["review_points_count"] == 0
    assert isinstance(res.data["review_points_count"], int)
    assert res.data["table_id"] == str(ti_dataset.table_id)


@pytest.mark.django_db
def test_metadata_review_points_table_id_empty_when_dataset_has_no_table(auth_client, ti_job):
    ds = NormalizedDataset.objects.create(
        workspace_id="ws-ti",
        job=ti_job,
        table=None,
        schema_version="0.1",
        dataset_payload={},
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
    url = reverse(
        "ti-metadata-review-points",
        kwargs={"metadata_id": meta.metadata_id},
    )
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["table_id"] == ""
    assert isinstance(res.data["table_id"], str)
    assert res.data["dataset_id"] == str(ds.dataset_id)
    assert res.data["review_points"] == []


@pytest.mark.django_db
def test_metadata_review_points_dataset_id_empty_when_no_dataset_fk(auth_client):
    """FK が無い場合は dataset_id は空文字（契約）。DB 通常行では埋まるが分岐を固定する。"""
    mid = uuid.uuid4()
    mock_meta = MagicMock()
    mock_meta.metadata_id = mid
    mock_meta.review_points = [{"id": "rp1", "severity": "warn"}]
    mock_meta.review_required = False
    mock_meta.dataset_id = None
    url = reverse("ti-metadata-review-points", kwargs={"metadata_id": mid})
    with patch(
        "table_intelligence.views.get_object_or_404",
        return_value=mock_meta,
    ):
        res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["dataset_id"] == ""
    assert res.data["table_id"] == ""
    assert res.data["review_points"] == [{"id": "rp1", "severity": "warn"}]
    assert res.data["review_points_count"] == len(res.data["review_points"]) == 1


@pytest.mark.django_db
def test_tables_404_unknown_id(auth_client):
    missing = uuid.uuid4()
    for name in (
        "ti-table-summary",
        "ti-table-read-artifact",
        "ti-table-decision",
        "ti-table-artifacts",
    ):
        url = reverse(name, kwargs={"table_id": missing})
        assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_review_points_404_unknown_id(auth_client):
    url = reverse(
        "ti-metadata-review-points",
        kwargs={"metadata_id": uuid.uuid4()},
    )
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_tables_unauthenticated_401(api_client, ti_table):
    url = reverse("ti-table-summary", kwargs={"table_id": ti_table.table_id})
    assert api_client.get(url).status_code == 401


@pytest.mark.django_db
def test_table_artifacts_two_datasets_order(auth_client, ti_job, ti_table):
    """新しい dataset が items[0] に来ること。"""
    ds_old = NormalizedDataset.objects.create(
        workspace_id="ws-ti",
        job=ti_job,
        table=ti_table,
        schema_version="0.1",
        dataset_payload={"tag": "old"},
    )
    AnalysisMetadata.objects.create(
        dataset=ds_old,
        workspace_id="ws-ti",
        review_required=False,
        review_points=[],
        dimensions=[],
        measures=[],
        decision={},
    )
    ds_new = NormalizedDataset.objects.create(
        workspace_id="ws-ti",
        job=ti_job,
        table=ti_table,
        schema_version="0.1",
        dataset_payload={"tag": "new"},
    )
    AnalysisMetadata.objects.create(
        dataset=ds_new,
        workspace_id="ws-ti",
        review_required=False,
        review_points=[],
        dimensions=[],
        measures=[],
        decision={},
    )
    url = reverse("ti-table-artifacts", kwargs={"table_id": ti_table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert len(res.data["items"]) == 2
    assert res.data["items"][0]["dataset_id"] == str(ds_new.dataset_id)
    assert res.data["items"][1]["dataset_id"] == str(ds_old.dataset_id)
