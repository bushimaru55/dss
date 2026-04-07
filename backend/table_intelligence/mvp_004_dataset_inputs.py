"""
004 MVP: ``NormalizedDataset.dataset_payload`` の 003 成果物を **参照入力**として読むだけ。

- ``normalization_input_hints``（002→003 の意図）→ ``trace_map`` → ``rows`` → 任意の ``column_slots[]``（003 列カタログ）を要約する。
- dimensions / measures / grain の確定は行わない（``semantic_lock_in: false``）。
"""

from __future__ import annotations

from typing import Any

from table_intelligence.models import AnalysisMetadata, NormalizedDataset

MVP_004_DATASET_INPUT_OBSERVATION_SCHEMA_REF = "ti.mvp_004_dataset_input_observation.v1"
MVP_004_REVIEW_POINT_ID = "004-mvp-dataset-inputs-observed"
MVP_004_COLUMN_SLOTS_REVIEW_POINT_ID = "004-mvp-column-slots-referenced"


def trace_kind_counts(trace_map: object) -> dict[str, int]:
    if not isinstance(trace_map, list):
        return {}
    out: dict[str, int] = {}
    for item in trace_map:
        if not isinstance(item, dict):
            continue
        k = str(item.get("kind") or "unknown")
        out[k] = out.get(k, 0) + 1
    return out


def summarize_column_slots_for_observation(column_slots: object) -> dict[str, Any]:
    """``dataset_payload.column_slots`` の参照用サマリ（004 意味確定ではない）。"""
    cs_ok = isinstance(column_slots, list)
    out: dict[str, Any] = {
        "read": cs_ok,
        "entry_count": len(column_slots) if cs_ok else 0,
        "hints_from_002_present_count": 0,
        "slot_id_values_key_preview": [],
    }
    if not cs_ok:
        return out
    hints_n = 0
    preview: list[dict[str, Any]] = []
    for item in column_slots:
        if not isinstance(item, dict):
            continue
        if item.get("hint_from_002") is not None:
            hints_n += 1
    out["hints_from_002_present_count"] = hints_n
    for item in column_slots[:8]:
        if not isinstance(item, dict):
            continue
        preview.append(
            {
                "slot_id": item.get("slot_id"),
                "values_key": item.get("values_key"),
                "has_hint_from_002": item.get("hint_from_002") is not None,
            }
        )
    out["slot_id_values_key_preview"] = preview
    return out


def build_mvp_004_dataset_input_observation(dataset_payload: dict[str, Any]) -> dict[str, Any]:
    """
    004 が読んだ入力の **観測サマリ**（確定結果ではない）。

    参照順: ``normalization_input_hints`` → ``trace_map`` → ``rows`` → ``column_slots``。
    """
    hints = dataset_payload.get("normalization_input_hints")
    trace_map = dataset_payload.get("trace_map")
    rows = dataset_payload.get("rows")
    column_slots = dataset_payload.get("column_slots")

    hints_ok = isinstance(hints, dict)
    trace_ok = isinstance(trace_map, list)
    rows_ok = isinstance(rows, list)

    hints_summary: dict[str, Any] = {"read": hints_ok}
    if hints_ok:
        by_r = hints.get("by_row_index") or {}
        by_c = hints.get("by_column_index") or {}
        hints_summary["schema_ref"] = hints.get("schema_ref")
        hints_summary["by_row_index_count"] = (
            len(by_r) if isinstance(by_r, dict) else 0
        )
        hints_summary["by_column_index_count"] = (
            len(by_c) if isinstance(by_c, dict) else 0
        )

    trace_summary: dict[str, Any] = {
        "read": trace_ok,
        "entry_count": len(trace_map) if trace_ok else 0,
        "kind_counts": trace_kind_counts(trace_map) if trace_ok else {},
    }

    value_keys_preview: list[str] = []
    if rows_ok and rows:
        first = rows[0]
        if isinstance(first, dict):
            vals = first.get("values")
            if isinstance(vals, dict):
                value_keys_preview = sorted(vals.keys())[:12]

    rows_preview: dict[str, Any] = {
        "read": rows_ok,
        "data_row_count": len(rows) if rows_ok else 0,
        "first_row_value_keys_preview": value_keys_preview,
    }

    column_slots_summary = summarize_column_slots_for_observation(column_slots)

    return {
        "schema_ref": MVP_004_DATASET_INPUT_OBSERVATION_SCHEMA_REF,
        "normalization_input_hints_summary": hints_summary,
        "trace_map_summary": trace_summary,
        "rows_preview": rows_preview,
        "column_slots_summary": column_slots_summary,
        "semantic_lock_in": False,
        "note": (
            "004 MVP: summarized dataset_payload from 003; not dimension/measure/grain lock-in"
        ),
    }


def apply_mvp_004_dataset_input_reflection(
    *, metadata: AnalysisMetadata, dataset: NormalizedDataset
) -> None:
    """
    ``dataset.dataset_payload`` を読み、``metadata.decision`` と ``review_points`` に痕跡を残す。

    ``decision["block"]`` 等の既存 MVP 値は維持し、観測は ``mvp_dataset_input_observation`` に載せる。
    """
    payload = dataset.dataset_payload if isinstance(dataset.dataset_payload, dict) else {}
    observation = build_mvp_004_dataset_input_observation(payload)

    decision = dict(metadata.decision) if isinstance(metadata.decision, dict) else {}
    decision["mvp_dataset_input_observation"] = observation

    rps = list(metadata.review_points) if isinstance(metadata.review_points, list) else []
    if not any(
        isinstance(p, dict) and p.get("point_id") == MVP_004_REVIEW_POINT_ID for p in rps
    ):
        rps.append(
            {
                "point_id": MVP_004_REVIEW_POINT_ID,
                "category": "DATASET_INPUT_REFERENCE",
                "priority": 2,
                "semantic_lock_in": False,
                "note": (
                    "004 read normalization_input_hints, trace_map, rows, and column_slots "
                    "from NormalizedDataset (003 output); reference only, not meaning lock-in"
                ),
            }
        )

    css = observation.get("column_slots_summary")
    if (
        isinstance(css, dict)
        and css.get("read")
        and int(css.get("entry_count") or 0) > 0
        and not any(
            isinstance(p, dict) and p.get("point_id") == MVP_004_COLUMN_SLOTS_REVIEW_POINT_ID
            for p in rps
        )
    ):
        rps.append(
            {
                "point_id": MVP_004_COLUMN_SLOTS_REVIEW_POINT_ID,
                "category": "DATASET_INPUT_REFERENCE",
                "priority": 3,
                "semantic_lock_in": False,
                "note": (
                    "004 read dataset_payload.column_slots (003 column catalog); "
                    "not dimensions/measures mapping"
                ),
            }
        )

    metadata.decision = decision
    metadata.review_points = rps
    metadata.save(update_fields=["decision", "review_points", "updated_at"])
