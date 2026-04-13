"""003 への 002 evidence ヒント抽出。"""

from __future__ import annotations

from types import SimpleNamespace

from table_intelligence.normalization_hints import (
    NORMALIZATION_HINTS_SCHEMA_REF,
    build_mvp_rows_and_trace_map_from_hints,
    extract_normalization_input_hints_from_judgment_evidence,
    merge_hints_into_dataset_payload,
    read_normalization_input_hints_from_dataset_payload,
)

# MVP column_slots 契約: 意味確定フィールドを持たない許可キーのみ
_MVP_SLOT_ALLOWED_KEYS = frozenset(
    {
        "slot_id",
        "table_column_index",
        "values_key",
        "semantic_lock_in",
        "hint_from_002",
        "trace_kind_preview",
        "trace_ref_ids",
    }
)


def _assert_mvp_column_slots_contract(slots: list) -> None:
    """列カタログ / 参照面であり dimension・measure 確定でないことの最小チェック。"""
    for s in slots:
        assert isinstance(s, dict)
        assert s.get("semantic_lock_in") is False
        assert set(s.keys()) <= _MVP_SLOT_ALLOWED_KEYS
        if "trace_kind_preview" in s:
            assert isinstance(s["trace_kind_preview"], list)
            assert all(isinstance(x, str) for x in s["trace_kind_preview"])
        if "trace_ref_ids" in s:
            assert isinstance(s["trace_ref_ids"], list)
            assert all(isinstance(x, str) for x in s["trace_ref_ids"])
        if "hint_from_002" in s:
            assert isinstance(s["hint_from_002"], str)


def test_extract_merges_row_col_from_evidence():
    ev = [
        {
            "rule_id": "J2-ROW-001",
            "details": {
                "primary_labels_schema": "ti.judgment.primary_labels.v1",
                "intent": "normalization_input_hints_not_semantic_lock_in",
                "by_row_index": {"0": "ROW_HEADER_BAND"},
            },
        },
        {
            "rule_id": "J2-COL-001",
            "details": {
                "by_column_index": {"0": "COL_ATTRIBUTE"},
            },
        },
    ]
    h = extract_normalization_input_hints_from_judgment_evidence(ev)
    assert h is not None
    assert h["schema_ref"] == NORMALIZATION_HINTS_SCHEMA_REF
    assert h["by_row_index"]["0"] == "ROW_HEADER_BAND"
    assert h["by_column_index"]["0"] == "COL_ATTRIBUTE"


def test_extract_returns_none_when_missing():
    assert extract_normalization_input_hints_from_judgment_evidence([]) is None
    assert (
        extract_normalization_input_hints_from_judgment_evidence(
            [{"rule_id": "J2-TAX-001", "details": {}}]
        )
        is None
    )


def test_merge_preserves_rows():
    p = merge_hints_into_dataset_payload(
        {"rows": [], "trace_map": []},
        {"schema_ref": "x", "by_row_index": {"0": "ROW_DETAIL"}},
    )
    assert p["rows"] == []
    assert p["normalization_input_hints"]["by_row_index"]["0"] == "ROW_DETAIL"


def test_build_mvp_skips_header_puts_col_hints():
    hints = {
        "by_row_index": {
            "0": "ROW_HEADER_BAND",
            "1": "ROW_DETAIL",
        },
        "by_column_index": {
            "0": "COL_ATTRIBUTE_CANDIDATE",
            "1": "COL_MEASURE_CANDIDATE",
        },
    }
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(hints, table=None)
    assert len(rows) == 1
    assert rows[0]["table_row_index"] == 1
    kinds = [t.get("kind") for t in trace]
    assert "header_band_skipped" in kinds
    assert "attribute_column_candidate" in kinds
    assert "measure_column_candidate" in kinds
    assert meta["data_row_count"] == 1
    assert meta["skipped_row_trace_count"] == 1
    assert len(slots) == 2
    assert {s["table_column_index"] for s in slots} == {0, 1}
    assert {s["values_key"] for s in slots} == {"c0", "c1"}
    _assert_mvp_column_slots_contract(slots)


def test_build_mvp_note_candidate_trace():
    hints = {
        "by_row_index": {"0": "ROW_DETAIL", "2": "ROW_NOTE_CANDIDATE"},
        "by_column_index": {},
    }
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(hints, table=None)
    assert any(t.get("kind") == "note_candidate" for t in trace)
    assert meta["skipped_row_trace_count"] == 1
    assert slots == []


def test_build_mvp_empty_row_col_hints_minimal_output():
    hints = {"by_row_index": {}, "by_column_index": {}}
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(hints, table=None)
    assert rows == [] and trace == []
    assert slots == []


def test_build_mvp_transcribes_cells_for_data_rows_only():
    hints = {
        "by_row_index": {
            "0": "ROW_HEADER_BAND",
            "1": "ROW_DETAIL",
        },
        "by_column_index": {},
    }
    cells = {
        "R0C0": {"raw_display": "hdr", "r": 0, "c": 0},
        "R1C0": {"raw_display": "a", "r": 1, "c": 0},
        "R1C1": {"raw_display": "42", "r": 1, "c": 1},
    }
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=cells
    )
    assert len(rows) == 1
    assert rows[0]["table_row_index"] == 1
    assert rows[0]["values"] == {"c0": "a", "c1": "42"}
    tx = [t for t in trace if t.get("kind") == "cell_value_transcribed"]
    assert len(tx) == 2
    assert meta.get("transcribed_cell_trace_count") == 2
    assert not any(t.get("table_row_index") == 0 for t in tx)
    assert len(slots) == 2
    by_idx = {s["table_column_index"]: s for s in slots}
    assert by_idx[1]["values_key"] == "c1"
    assert "hint_from_002" not in by_idx[1]
    assert "cell_value_transcribed" in (by_idx[1].get("trace_kind_preview") or [])
    _assert_mvp_column_slots_contract(slots)


def test_build_mvp_no_cells_leaves_values_empty():
    hints = {"by_row_index": {"0": "ROW_DETAIL"}, "by_column_index": {}}
    rows, _, meta, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=None
    )
    assert rows[0]["values"] == {}
    assert meta.get("transcribed_cell_trace_count") == 0
    assert slots == []


def test_column_slots_union_hints_and_transcribed_only():
    """by_column_index にのみある列と、転記のみの列の和集合。"""
    hints = {
        "by_row_index": {"0": "ROW_DETAIL"},
        "by_column_index": {"2": "COL_UNKNOWN"},
    }
    cells = {"R0C0": {"raw_display": "a", "r": 0, "c": 0}}
    rows, _, _, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=cells
    )
    assert rows[0]["values"] == {"c0": "a"}
    idxs = {s["table_column_index"] for s in slots}
    assert idxs == {0, 2}
    s0 = next(s for s in slots if s["table_column_index"] == 0)
    s2 = next(s for s in slots if s["table_column_index"] == 2)
    assert s0["values_key"] == "c0"
    assert s2["values_key"] == "c2"
    assert s2["hint_from_002"] == "COL_UNKNOWN"
    assert "cell_value_transcribed" in s0.get("trace_kind_preview", [])
    _assert_mvp_column_slots_contract(slots)


def test_mvp_column_slots_by_column_index_only_no_transcription():
    """転記なしでも by_column_index の列だけで slot が立つ（和集合の片側）。"""
    hints = {
        "by_row_index": {
            "0": "ROW_HEADER_BAND",
            "1": "ROW_HEADER_BAND",
        },
        "by_column_index": {"4": "COL_NOTE"},
    }
    rows, _, _, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=None
    )
    assert rows == []
    assert {s["table_column_index"] for s in slots} == {4}
    s4 = slots[0]
    assert s4["values_key"] == "c4"
    assert s4["hint_from_002"] == "COL_NOTE"
    assert "trace_kind_preview" in s4
    _assert_mvp_column_slots_contract(slots)


def test_mvp_column_slots_transcription_only_column_set_follows_cells():
    """by_column_index が空なら slot 集合は転記 cN のみ（セル範囲で列集合が変わる）。"""
    hints = {"by_row_index": {"0": "ROW_DETAIL"}, "by_column_index": {}}
    _, _, _, slots_one = build_mvp_rows_and_trace_map_from_hints(
        hints,
        table=None,
        cells={"R0C0": {"raw_display": "a", "r": 0, "c": 0}},
    )
    assert {s["table_column_index"] for s in slots_one} == {0}
    _, _, _, slots_two = build_mvp_rows_and_trace_map_from_hints(
        hints,
        table=None,
        cells={
            "R0C0": {"raw_display": "a", "r": 0, "c": 0},
            "R0C1": {"raw_display": "b", "r": 0, "c": 1},
        },
    )
    assert {s["table_column_index"] for s in slots_two} == {0, 1}
    _assert_mvp_column_slots_contract(slots_one)
    _assert_mvp_column_slots_contract(slots_two)


def test_mvp_column_slots_union_explicit_by_col_and_transcription():
    """契約正本: by_column_index 列キー ∪ 転記 cN 列（和集合）。"""
    hints = {
        "by_row_index": {"0": "ROW_DETAIL"},
        "by_column_index": {"1": "COL_MEASURE_CANDIDATE"},
    }
    rows, _, _, slots = build_mvp_rows_and_trace_map_from_hints(
        hints,
        table=None,
        cells={"R0C0": {"raw_display": "x", "r": 0, "c": 0}},
    )
    assert rows[0]["values"] == {"c0": "x"}
    assert {s["table_column_index"] for s in slots} == {0, 1}
    s0 = next(s for s in slots if s["table_column_index"] == 0)
    s1 = next(s for s in slots if s["table_column_index"] == 1)
    assert "hint_from_002" not in s0
    assert s1["hint_from_002"] == "COL_MEASURE_CANDIDATE"
    _assert_mvp_column_slots_contract(slots)


def test_mvp_column_slots_trace_ref_ids_are_trace_map_subset():
    """trace_ref_ids / trace_kind_preview は trace_map 由来の説明用参照（業務意味の確定ではない）。"""
    hints = {
        "by_row_index": {"0": "ROW_DETAIL"},
        "by_column_index": {"0": "COL_ATTRIBUTE_CANDIDATE"},
    }
    cells = {"R0C0": {"raw_display": "v", "r": 0, "c": 0}}
    _, trace, _, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=cells
    )
    s0 = next(s for s in slots if s["table_column_index"] == 0)
    refs = set(s0.get("trace_ref_ids") or [])
    kinds = set(s0.get("trace_kind_preview") or [])
    trace_refs = {
        t.get("trace_ref")
        for t in trace
        if isinstance(t, dict) and isinstance(t.get("trace_ref"), str)
    }
    trace_kinds = {
        t.get("kind")
        for t in trace
        if isinstance(t, dict) and isinstance(t.get("kind"), str)
    }
    assert refs <= trace_refs
    assert kinds <= trace_kinds
    assert "cell_value_transcribed" in kinds
    assert "attribute_column_candidate" in kinds
    _assert_mvp_column_slots_contract(slots)


def test_mvp_column_slots_row_skip_hint_column_without_transcription():
    """行構成で転記列が減っても、by_column_index の列は slot に残る（和集合）。"""
    hints = {
        "by_row_index": {
            "0": "ROW_HEADER_BAND",
            "1": "ROW_DETAIL",
        },
        "by_column_index": {"0": "COL_ATTRIBUTE_CANDIDATE", "1": "COL_MEASURE_CANDIDATE"},
    }
    cells = {"R1C0": {"raw_display": "only0", "r": 1, "c": 0}}
    rows, _, _, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=cells
    )
    assert rows[0]["values"] == {"c0": "only0"}
    assert {s["table_column_index"] for s in slots} == {0, 1}
    s1 = next(s for s in slots if s["table_column_index"] == 1)
    assert s1.get("hint_from_002") == "COL_MEASURE_CANDIDATE"
    assert "cell_value_transcribed" not in (s1.get("trace_kind_preview") or [])
    _assert_mvp_column_slots_contract(slots)


def test_read_hints_from_payload():
    p = {"normalization_input_hints": {"by_row_index": {"0": "ROW_HEADER_BAND"}}}
    h = read_normalization_input_hints_from_dataset_payload(p)
    assert h is not None
    assert h["by_row_index"]["0"] == "ROW_HEADER_BAND"


def test_build_mvp_table_scope_row_range_when_by_row_empty():
    """by_row_index が空のとき TableScope.row_min/max で行走査（各行情報は ROW_UNKNOWN）。"""
    hints = {"by_row_index": {}, "by_column_index": {}}
    table = SimpleNamespace(row_min=2, row_max=4)
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=table, cells=None
    )
    assert [r["table_row_index"] for r in rows] == [2, 3, 4]
    assert all(
        r["normalization_hint"]["from_002_row_kind"] == "ROW_UNKNOWN" for r in rows
    )
    assert all(
        r["normalization_hint"]["row_index_enumeration_source"]
        == "table_scope_row_range_fallback"
        for r in rows
    )
    assert all(r["values"] == {} for r in rows)
    assert len(trace) == 1
    assert trace[0].get("kind") == "row_index_enumeration_source"
    assert trace[0].get("mvp_input_provenance") == "table_scope_row_range_fallback"
    assert trace[0].get("table_row_min") == 2 and trace[0].get("table_row_max") == 4
    assert slots == []
    assert meta.get("transcribed_cell_trace_count") == 0
    assert meta.get("data_row_count") == 3


def test_build_mvp_aggregate_rows_skipped_trace_not_in_rows():
    """集計行は skipped_row_candidate のみ残り、rows[] には含めない。"""
    hints = {
        "by_row_index": {
            "0": "ROW_SUBTOTAL",
            "1": "ROW_GRAND_TOTAL",
            "2": "ROW_DETAIL",
        },
        "by_column_index": {},
    }
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=None
    )
    assert len(rows) == 1
    assert rows[0]["table_row_index"] == 2
    assert rows[0]["values"] == {}
    skip_traces = [t for t in trace if t.get("kind") == "skipped_row_candidate"]
    assert len(skip_traces) == 2
    assert {t.get("table_row_index") for t in skip_traces} == {0, 1}
    assert meta["skipped_row_trace_count"] == 2
    assert meta["data_row_count"] == 1
    assert slots == []


def test_build_mvp_row_unknown_data_row_empty_values():
    """ROW_UNKNOWN はデータ行として rows[] に入りうる（cells なしなら values は空）。"""
    hints = {"by_row_index": {"7": "ROW_UNKNOWN"}, "by_column_index": {}}
    rows, trace, meta, slots = build_mvp_rows_and_trace_map_from_hints(
        hints, table=None, cells=None
    )
    assert len(rows) == 1
    assert rows[0]["table_row_index"] == 7
    assert rows[0]["logical_row_index"] == 0
    assert rows[0]["values"] == {}
    assert rows[0]["normalization_hint"]["from_002_row_kind"] == "ROW_UNKNOWN"
    assert rows[0]["normalization_hint"].get("semantic_lock_in") is False
    assert (
        rows[0]["normalization_hint"]["row_index_enumeration_source"]
        == "normalization_input_hints_by_row_index"
    )
    assert trace == []
    assert slots == []
    assert meta.get("transcribed_cell_trace_count") == 0
