"""
MVP: POST job から dataset / metadata / evaluation / session / suggestion までの E2E。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_mvp_pipeline_e2e.py
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from table_intelligence.judgment_spike import JUDGE_PROFILE_SPIKE
from table_intelligence.models import (
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


@pytest.mark.django_db
def test_post_job_materializes_chain_and_gets_resolve(auth_client, user):
    url_create = reverse("ti-table-analysis-job-create")
    res = auth_client.post(
        url_create,
        {"workspace_id": "ws-e2e", "request_payload": {"case": "e2e"}},
        format="json",
    )
    assert res.status_code == 202
    job_id = res.data["job_id"]
    refs = res.data["artifact_refs"]

    url_job = reverse("ti-table-analysis-job-detail", kwargs={"job_id": job_id})
    dres = auth_client.get(url_job)
    assert dres.status_code == 200
    assert dres.data["status"] == JobStatus.SUCCEEDED
    assert dres.data["artifact_refs"]["metadata_id"] == refs["metadata_id"]
    assert dres.data["request_payload"]["mvp_pipeline"]["metadata_id"] == refs["metadata_id"]

    assert TableScope.objects.filter(pk=refs["table_id"]).count() == 1
    assert TableReadArtifact.objects.filter(table_id=refs["table_id"], is_latest=True).count() == 1
    ra = TableReadArtifact.objects.get(table_id=refs["table_id"], is_latest=True)
    assert "R0C0" in ra.cells
    assert ra.merges == []
    assert ra.parse_warnings == []
    assert JudgmentResult.objects.filter(table_id=refs["table_id"], is_latest=True).count() == 1
    jrow = JudgmentResult.objects.get(table_id=refs["table_id"], is_latest=True)
    assert jrow.decision == JudgmentDecision.NEEDS_REVIEW
    assert jrow.taxonomy_code == TI_TABLE_UNKNOWN
    assert len(jrow.evidence) >= 1
    tax_ev = next(e for e in jrow.evidence if e.get("rule_id") == "J2-TAX-001")
    assert tax_ev["details"].get("judge_profile_id") == JUDGE_PROFILE_SPIKE
    assert NormalizedDataset.objects.filter(pk=refs["dataset_id"]).count() == 1
    nds = NormalizedDataset.objects.get(pk=refs["dataset_id"])
    nh = nds.dataset_payload.get("normalization_input_hints")
    assert nh is not None
    assert nh.get("schema_ref") == "ti.normalization_hints.v1"
    assert nh.get("intent") == "normalization_input_hints_not_semantic_lock_in"
    assert "by_row_index" in nh and "by_column_index" in nh
    assert isinstance(nds.dataset_payload.get("rows"), list)
    assert isinstance(nds.dataset_payload.get("trace_map"), list)
    assert nds.dataset_payload.get("mvp_normalization_stub", {}).get("schema_ref") == (
        "ti.mvp_normalization_stub.v1"
    )
    kinds = {t.get("kind") for t in (nds.dataset_payload.get("trace_map") or [])}
    assert kinds
    assert kinds <= {
        "header_band_skipped",
        "note_candidate",
        "skipped_row_candidate",
        "attribute_column_candidate",
        "measure_column_candidate",
        "column_role_hint",
        "cell_value_transcribed",
    }
    rows_out = nds.dataset_payload.get("rows") or []
    assert rows_out
    assert "c0" in rows_out[0].get("values", {})
    assert nds.dataset_payload.get("mvp_normalization_stub", {}).get(
        "transcribed_cell_trace_count", 0
    ) >= 1
    column_slots = nds.dataset_payload.get("column_slots")
    assert isinstance(column_slots, list) and len(column_slots) >= 1
    slot0 = next(s for s in column_slots if s.get("table_column_index") == 0)
    assert slot0.get("slot_id") == "col_0"
    assert slot0.get("values_key") == "c0"
    assert nds.dataset_payload.get("mvp_normalization_stub", {}).get(
        "column_slots_schema_ref"
    ) == "ti.mvp_column_slots.v1"
    meta = AnalysisMetadata.objects.get(pk=refs["metadata_id"])
    assert meta.review_required is True
    assert len(meta.review_points) >= 1
    assert meta.decision.get("block") == "004-mvp-placeholder"
    obs = meta.decision.get("mvp_dataset_input_observation")
    assert isinstance(obs, dict)
    assert obs.get("schema_ref") == "ti.mvp_004_dataset_input_observation.v1"
    assert obs.get("semantic_lock_in") is False
    assert obs.get("normalization_input_hints_summary", {}).get("read") is True
    assert obs.get("trace_map_summary", {}).get("entry_count", 0) >= 1
    css = obs.get("column_slots_summary") or {}
    assert css.get("read") is True
    assert css.get("entry_count", 0) >= 1
    assert css.get("hints_from_002_present_count", 0) >= 1
    assert isinstance(css.get("slot_id_values_key_preview"), list)
    assert any(
        p.get("point_id") == "004-mvp-dataset-inputs-observed"
        for p in (meta.review_points or [])
        if isinstance(p, dict)
    )
    assert any(
        p.get("point_id") == "004-mvp-column-slots-referenced"
        for p in (meta.review_points or [])
        if isinstance(p, dict)
    )

    assert ConfidenceEvaluation.objects.filter(pk=refs["evaluation_ref"]).count() == 1
    ev = ConfidenceEvaluation.objects.get(pk=refs["evaluation_ref"])
    assert ev.decision_recommendation.get("source") == "011-mvp-stub"

    assert HumanReviewSession.objects.filter(pk=refs["session_id"]).count() == 1
    sess = HumanReviewSession.objects.get(pk=refs["session_id"])
    assert str(sess.metadata_id) == refs["metadata_id"]

    assert SuggestionSet.objects.filter(pk=refs["suggestion_run_ref"]).count() == 1
    sset = SuggestionSet.objects.get(pk=refs["suggestion_run_ref"])
    assert str(sset.metadata_id) == refs["metadata_id"]
    assert len(sset.analysis_candidates) >= 1

    url_meta = reverse("ti-metadata-detail", kwargs={"metadata_id": refs["metadata_id"]})
    assert auth_client.get(url_meta).status_code == 200

    url_eval = reverse("ti-evaluation-detail", kwargs={"evaluation_ref": refs["evaluation_ref"]})
    eres = auth_client.get(url_eval)
    assert eres.status_code == 200
    assert "decision_recommendation" in eres.data
    assert "decision" not in eres.data

    url_sess = reverse("ti-review-session-detail", kwargs={"session_id": refs["session_id"]})
    assert auth_client.get(url_sess).status_code == 200

    url_sug = reverse("ti-suggestion-set-detail", kwargs={"suggestion_run_ref": refs["suggestion_run_ref"]})
    assert auth_client.get(url_sug).status_code == 200

    url_decision = reverse("ti-table-decision", kwargs={"table_id": refs["table_id"]})
    dres = auth_client.get(url_decision)
    assert dres.status_code == 200
    assert dres.data["decision"] == JudgmentDecision.NEEDS_REVIEW
    assert dres.data["taxonomy_code"] == TI_TABLE_UNKNOWN
    assert len(dres.data["evidence"]) >= 1
    assert any(e.get("rule_id") == "J2-TAX-001" for e in dres.data["evidence"])
    assert "decision_recommendation" not in dres.data

    url_read = reverse("ti-table-read-artifact", kwargs={"table_id": refs["table_id"]})
    rres = auth_client.get(url_read)
    assert rres.status_code == 200
    assert rres.data["artifact_id"] == str(ra.artifact_id)
    assert rres.data["table_id"] == refs["table_id"]
    assert "R0C0" in rres.data["cells"]
    assert rres.data["merges"] == []
    assert rres.data["parse_warnings"] == []
