"""004 MVP: dataset_payload 参照入力の観測。"""

from __future__ import annotations

import pytest

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    JobStatus,
    NormalizedDataset,
    TableScope,
)
from table_intelligence.mvp_004_dataset_inputs import (
    MVP_004_COLUMN_SLOTS_REVIEW_POINT_ID,
    MVP_004_DATASET_INPUT_OBSERVATION_SCHEMA_REF,
    MVP_004_REVIEW_POINT_ID,
    apply_mvp_004_dataset_input_reflection,
    build_mvp_004_dataset_input_observation,
    summarize_column_slots_for_observation,
    trace_kind_counts,
    trace_mvp_input_provenance_counts,
    trace_row_index_fallback_banner_present,
)


def test_trace_kind_counts_empty():
    assert trace_kind_counts(None) == {}
    assert trace_kind_counts("x") == {}
    assert trace_kind_counts([{"kind": "a"}, {"kind": "a"}, {}]) == {"a": 2, "unknown": 1}


def test_trace_mvp_input_provenance_counts_and_fallback_banner():
    tm = [
        {"kind": "row_index_enumeration_source", "mvp_input_provenance": "table_scope_row_range_fallback"},
        {"kind": "x", "mvp_input_provenance": "normalization_input_hints"},
    ]
    assert trace_mvp_input_provenance_counts(tm) == {
        "table_scope_row_range_fallback": 1,
        "normalization_input_hints": 1,
    }
    assert trace_row_index_fallback_banner_present(tm) is True
    assert trace_row_index_fallback_banner_present([{"kind": "cell_value_transcribed"}]) is False


def test_build_observation_order_and_preview():
    payload = {
        "normalization_input_hints": {
            "schema_ref": "ti.normalization_hints.v1",
            "by_row_index": {"0": "ROW_DETAIL"},
            "by_column_index": {"1": "COL_MEASURE_CANDIDATE"},
        },
        "trace_map": [{"kind": "cell_value_transcribed", "table_row_index": 0}],
        "rows": [{"values": {"c1": "x", "c0": "y"}}],
    }
    obs = build_mvp_004_dataset_input_observation(payload)
    assert obs["schema_ref"] == MVP_004_DATASET_INPUT_OBSERVATION_SCHEMA_REF
    assert obs["semantic_lock_in"] is False
    h = obs["normalization_input_hints_summary"]
    assert h["read"] is True
    assert h["by_row_index_count"] == 1
    assert h["by_column_index_count"] == 1
    t = obs["trace_map_summary"]
    assert t["entry_count"] == 1
    assert t["kind_counts"]["cell_value_transcribed"] == 1
    assert obs["rows_preview"]["first_row_value_keys_preview"] == ["c0", "c1"]
    css = obs["column_slots_summary"]
    assert css["read"] is False
    assert css["entry_count"] == 0
    assert obs["trace_map_summary"]["mvp_input_provenance_counts"] == {}
    assert obs["trace_map_summary"]["row_index_fallback_trace_present"] is False
    assert obs["rows_preview"]["row_index_enumeration_source_counts"] == {}
    assert obs["rows_preview"]["normalization_hint_semantic_lock_in_non_false_count"] == 0
    assert obs.get("payload_root_semantic_lock_in") is None
    assert obs.get("uncertainty_provenance_note")


def test_build_observation_003_provenance_minimal_path():
    """003 相当の provenance 付き payload を 004 が観測する（意味確定はしない）。"""
    payload = {
        "normalization_input_hints": {
            "schema_ref": "ti.normalization_hints.v1",
            "by_row_index": {"0": "ROW_DETAIL"},
            "by_column_index": {},
        },
        "trace_map": [
            {
                "kind": "cell_value_transcribed",
                "mvp_input_provenance": "cells_raw_display",
                "semantic_lock_in": False,
            }
        ],
        "rows": [
            {
                "values": {"c0": "x"},
                "normalization_hint": {
                    "from_002_row_kind": "ROW_DETAIL",
                    "semantic_lock_in": False,
                    "row_index_enumeration_source": "normalization_input_hints_by_row_index",
                },
            }
        ],
    }
    obs = build_mvp_004_dataset_input_observation(payload)
    assert obs["semantic_lock_in"] is False
    assert obs["trace_map_summary"]["mvp_input_provenance_counts"] == {"cells_raw_display": 1}
    assert obs["trace_map_summary"]["row_index_fallback_trace_present"] is False
    assert obs["rows_preview"]["row_index_enumeration_source_counts"] == {
        "normalization_input_hints_by_row_index": 1,
    }


def test_build_observation_fallback_trace_and_row_enumeration_observed():
    payload = {
        "normalization_input_hints": {"by_row_index": {}, "by_column_index": {}},
        "trace_map": [
            {
                "kind": "row_index_enumeration_source",
                "mvp_input_provenance": "table_scope_row_range_fallback",
                "table_row_min": 2,
                "table_row_max": 4,
                "semantic_lock_in": False,
            },
        ],
        "rows": [
            {
                "values": {},
                "normalization_hint": {
                    "semantic_lock_in": False,
                    "row_index_enumeration_source": "table_scope_row_range_fallback",
                },
            }
        ],
    }
    obs = build_mvp_004_dataset_input_observation(payload)
    assert obs["trace_map_summary"]["row_index_fallback_trace_present"] is True
    assert obs["trace_map_summary"]["mvp_input_provenance_counts"] == {
        "table_scope_row_range_fallback": 1,
    }
    assert obs["rows_preview"]["row_index_enumeration_source_counts"] == {
        "table_scope_row_range_fallback": 1,
    }


def test_build_observation_column_slots_summary():
    payload = {
        "normalization_input_hints": {},
        "trace_map": [],
        "rows": [],
        "column_slots": [
            {
                "slot_id": "col_0",
                "table_column_index": 0,
                "values_key": "c0",
                "hint_from_002": "COL_ATTRIBUTE_CANDIDATE",
            },
            {"slot_id": "col_1", "table_column_index": 1, "values_key": "c1"},
        ],
    }
    obs = build_mvp_004_dataset_input_observation(payload)
    css = obs["column_slots_summary"]
    assert css["read"] is True
    assert css["entry_count"] == 2
    assert css["hints_from_002_present_count"] == 1
    assert css["slot_id_values_key_preview"][0]["has_hint_from_002"] is True
    assert css["slot_id_values_key_preview"][1]["has_hint_from_002"] is False
    assert css.get("semantic_lock_in_non_false_entry_count") == 0


def test_summarize_column_slots_invalid():
    s = summarize_column_slots_for_observation("nope")
    assert s["read"] is False and s["entry_count"] == 0


@pytest.mark.django_db
def test_apply_reflection_preserves_block_and_idempotent_review_point(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-004",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-004")
    dataset = NormalizedDataset.objects.create(
        job=job,
        table=table,
        workspace_id="ws-004",
        dataset_payload={
            "normalization_input_hints": {"schema_ref": "h", "by_row_index": {}},
            "trace_map": [],
            "rows": [],
        },
    )
    meta = AnalysisMetadata.objects.create(
        dataset=dataset,
        workspace_id="ws-004",
        review_required=True,
        review_points=[{"point_id": "mvp-1", "category": "MVP_PLACEHOLDER"}],
        dimensions=[],
        measures=[],
        decision={"block": "004-mvp-placeholder", "note": "stub"},
    )
    apply_mvp_004_dataset_input_reflection(metadata=meta, dataset=dataset)
    meta.refresh_from_db()
    assert meta.decision.get("block") == "004-mvp-placeholder"
    assert "mvp_dataset_input_observation" in meta.decision
    n_rp = len(meta.review_points)
    assert any(p.get("point_id") == MVP_004_REVIEW_POINT_ID for p in meta.review_points)
    apply_mvp_004_dataset_input_reflection(metadata=meta, dataset=dataset)
    meta.refresh_from_db()
    assert len(meta.review_points) == n_rp


@pytest.mark.django_db
def test_apply_adds_column_slots_review_point_when_catalog_present(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-004b",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-004b")
    dataset = NormalizedDataset.objects.create(
        job=job,
        table=table,
        workspace_id="ws-004b",
        dataset_payload={
            "normalization_input_hints": {"schema_ref": "h"},
            "trace_map": [],
            "rows": [],
            "column_slots": [
                {"slot_id": "col_0", "table_column_index": 0, "values_key": "c0"}
            ],
        },
    )
    meta = AnalysisMetadata.objects.create(
        dataset=dataset,
        workspace_id="ws-004b",
        review_required=True,
        review_points=[],
        dimensions=[],
        measures=[],
        decision={"block": "004-mvp-placeholder"},
    )
    apply_mvp_004_dataset_input_reflection(metadata=meta, dataset=dataset)
    meta.refresh_from_db()
    assert (
        meta.decision["mvp_dataset_input_observation"]["column_slots_summary"][
            "entry_count"
        ]
        == 1
    )
    pids = {p.get("point_id") for p in meta.review_points if isinstance(p, dict)}
    assert MVP_004_REVIEW_POINT_ID in pids
    assert MVP_004_COLUMN_SLOTS_REVIEW_POINT_ID in pids
