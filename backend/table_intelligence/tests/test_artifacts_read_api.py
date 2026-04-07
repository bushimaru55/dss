"""
Artifacts / metadata / evaluation の GET API テスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_artifacts_read_api.py
"""

from __future__ import annotations

import uuid

import pytest
from django.urls import reverse

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ConfidenceEvaluation,
    JobStatus,
    NormalizedDataset,
    TableScope,
)
from table_intelligence.mvp_004_dataset_inputs import apply_mvp_004_dataset_input_reflection


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
        review_points=[{"id": "p1"}],
        dimensions=[],
        measures=[],
        decision={"block": "004-not-judgment"},
    )


@pytest.fixture
def ti_evaluation(ti_metadata):
    return ConfidenceEvaluation.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        confidence_score=0.85,
        risk_signals=[{"code": "low_coverage"}],
        decision_recommendation={"level": "review", "source": "011"},
    )


@pytest.mark.django_db
def test_get_dataset(auth_client, ti_dataset):
    url = reverse("ti-dataset-detail", kwargs={"dataset_id": ti_dataset.dataset_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["dataset_id"] == str(ti_dataset.dataset_id)
    assert res.data["dataset_payload"] == {"rows": []}
    assert res.data["workspace_id"] == "ws-ti"


@pytest.mark.django_db
def test_get_dataset_404(auth_client):
    url = reverse("ti-dataset-detail", kwargs={"dataset_id": uuid.uuid4()})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_metadata(auth_client, ti_metadata, ti_dataset):
    url = reverse("ti-metadata-detail", kwargs={"metadata_id": ti_metadata.metadata_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["metadata_id"] == str(ti_metadata.metadata_id)
    assert res.data["dataset_id"] == str(ti_dataset.dataset_id)
    assert res.data["decision"] == {"block": "004-not-judgment"}
    assert "decision_recommendation" not in res.data


@pytest.mark.django_db
def test_get_metadata_404(auth_client):
    url = reverse("ti-metadata-detail", kwargs={"metadata_id": uuid.uuid4()})
    assert auth_client.get(url).status_code == 404


@pytest.mark.django_db
def test_get_metadata_exposes_mvp_004_dataset_input_observation(auth_client, user):
    """004 MVP: GET metadata が 003 参照観測（decision 拡張）を返す。"""
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    dataset = NormalizedDataset.objects.create(
        workspace_id="ws-ti",
        job=job,
        table=table,
        schema_version="0.1",
        dataset_payload={
            "normalization_input_hints": {
                "schema_ref": "ti.normalization_hints.v1",
                "by_row_index": {"0": "ROW_DETAIL"},
                "by_column_index": {"0": "COL_ATTRIBUTE_CANDIDATE"},
            },
            "trace_map": [{"kind": "cell_value_transcribed", "table_row_index": 0}],
            "rows": [{"values": {"c0": "x"}}],
            "column_slots": [
                {"slot_id": "col_0", "table_column_index": 0, "values_key": "c0"}
            ],
        },
    )
    meta = AnalysisMetadata.objects.create(
        dataset=dataset,
        workspace_id="ws-ti",
        review_required=True,
        review_points=[{"point_id": "mvp-1", "category": "MVP_PLACEHOLDER"}],
        dimensions=[],
        measures=[],
        decision={"block": "004-mvp-placeholder"},
    )
    apply_mvp_004_dataset_input_reflection(metadata=meta, dataset=dataset)

    url = reverse("ti-metadata-detail", kwargs={"metadata_id": meta.metadata_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    dec = res.data["decision"]
    assert dec.get("block") == "004-mvp-placeholder"
    obs = dec.get("mvp_dataset_input_observation")
    assert isinstance(obs, dict)
    assert obs.get("schema_ref") == "ti.mvp_004_dataset_input_observation.v1"
    assert obs.get("normalization_input_hints_summary", {}).get("read") is True
    assert obs.get("trace_map_summary", {}).get("entry_count") == 1
    assert obs.get("rows_preview", {}).get("first_row_value_keys_preview") == ["c0"]
    assert obs.get("column_slots_summary", {}).get("entry_count") == 1
    assert any(
        p.get("point_id") == "004-mvp-dataset-inputs-observed"
        for p in res.data["review_points"]
        if isinstance(p, dict)
    )
    assert any(
        p.get("point_id") == "004-mvp-column-slots-referenced"
        for p in res.data["review_points"]
        if isinstance(p, dict)
    )


@pytest.mark.django_db
def test_get_evaluation(auth_client, ti_evaluation, ti_metadata):
    url = reverse("ti-evaluation-detail", kwargs={"evaluation_ref": ti_evaluation.evaluation_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    assert res.data["evaluation_ref"] == str(ti_evaluation.evaluation_id)
    assert res.data["metadata_id"] == str(ti_metadata.metadata_id)
    assert res.data["decision_recommendation"] == {"level": "review", "source": "011"}
    assert "decision" not in res.data


@pytest.mark.django_db
def test_get_evaluation_404(auth_client):
    url = reverse("ti-evaluation-detail", kwargs={"evaluation_ref": uuid.uuid4()})
    assert auth_client.get(url).status_code == 404
