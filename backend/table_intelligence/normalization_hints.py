"""
003 正規化入力ヒント（002 ``JudgmentResult.evidence`` の J2-ROW / J2-COL を反映）。

004 の dimensions/measures 確定・011 の特徴量化は行わない。

**003 MVP パイプライン（このモジュール内）**
- ``read_normalization_input_hints_from_dataset_payload``: ``dataset_payload`` からの入口
- ``extract_normalization_input_hints_from_judgment_evidence``: 002 evidence → ヒント dict
- ``merge_hints_into_dataset_payload``: payload へのヒントマージ（I/O）
- ``assemble_mvp_003_dataset_payload_artifacts``: rows / trace_map / column_slots / stub メタの組立（services から呼ぶ）
- ``build_mvp_rows_and_trace_map_from_hints``: 上記成果物生成の公開ファサード（単体テスト・直接利用）
"""

from __future__ import annotations

import re
from typing import Any

# judgment_spike と整合
RULE_J2_ROW = "J2-ROW-001"
RULE_J2_COL = "J2-COL-001"

NORMALIZATION_HINTS_SCHEMA_REF = "ti.normalization_hints.v1"

MVP_NORMALIZATION_STUB_SCHEMA_REF = "ti.mvp_normalization_stub.v1"
MVP_COLUMN_SLOTS_SCHEMA_REF = "ti.mvp_column_slots.v1"

_AGG_ROW_KINDS_SKIP_DATA = frozenset({"ROW_SUBTOTAL", "ROW_GRAND_TOTAL"})

_RKEY = re.compile(r"^R(\d+)C(\d+)$")

# trace_map / normalization_hint で「どの入力筋か」を追う（意味確定ではない）
_PROV_HINTS = "normalization_input_hints"
_PROV_CELLS = "cells_raw_display"
_PROV_TABLE_SCOPE_FALLBACK = "table_scope_row_range_fallback"
_ROW_ENUM_FROM_HINT_KEYS = "normalization_input_hints_by_row_index"


def _sparse_cells_by_column_in_row(
    cells: dict[str, Any], row_index: int
) -> dict[int, dict[str, Any]]:
    """
    001 稀疏 ``cells`` のうち ``r == row_index`` のセルを列 index 昇順で返す（観測を改変しない）。
    """
    out: dict[int, dict[str, Any]] = {}
    for key, val in cells.items():
        if isinstance(val, dict) and "r" in val and "c" in val:
            try:
                if int(val["r"]) != row_index:
                    continue
                c = int(val["c"])
            except (TypeError, ValueError):
                continue
            out[c] = val
            continue
        m = _RKEY.match(str(key))
        if m and int(m.group(1)) == row_index:
            c = int(m.group(2))
            if isinstance(val, dict):
                out[c] = val
    return out


def _table_column_indices_from_values_keys(rows: list[dict[str, Any]]) -> set[int]:
    out: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        vals = row.get("values")
        if not isinstance(vals, dict):
            continue
        for k in vals:
            if not isinstance(k, str) or not k.startswith("c"):
                continue
            tail = k[1:]
            if tail.isdigit():
                out.add(int(tail))
    return out


def _mvp_coerce_row_column_maps(
    hints: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """``normalization_input_hints`` から ``by_row_index`` / ``by_column_index`` を正規化コピー。"""
    by_row: dict[str, str] = dict(hints.get("by_row_index") or {})
    by_col: dict[str, str] = dict(hints.get("by_column_index") or {})
    return by_row, by_col


def _mvp_resolve_table_row_indices(
    *,
    by_row_index: dict[str, str],
    table: Any | None,
) -> list[int]:
    """
    行走査順序を決める。

    - ``by_row_index`` に **1 件でも** キーがあれば、そのキーだけを昇順で使う（002 候補優先）。
    - **空 dict のときのみ** ``TableScope.row_min`` / ``row_max`` でレンジ列挙（MVP 契約の fallback）。
    """
    if by_row_index:
        return sorted(int(k) for k in by_row_index.keys())
    rm = getattr(table, "row_min", None) if table is not None else None
    rM = getattr(table, "row_max", None) if table is not None else None
    if rm is not None and rM is not None:
        return list(range(int(rm), int(rM) + 1))
    return []


def _trace_row_index_table_scope_fallback(*, row_min: int, row_max: int) -> dict[str, Any]:
    return {
        "trace_ref": "mvp-003-row-index-table-scope-fallback",
        "kind": "row_index_enumeration_source",
        "semantic_lock_in": False,
        "mvp_input_provenance": _PROV_TABLE_SCOPE_FALLBACK,
        "table_row_min": row_min,
        "table_row_max": row_max,
        "note": (
            "003: by_row_index empty; TableScope row_min/row_max used to enumerate "
            "table_row_index only; not normalization_input_hints lock-in"
        ),
    }


def _trace_header_band_skipped(table_row_index: int) -> dict[str, Any]:
    return {
        "trace_ref": f"mvp-header-band-{table_row_index}",
        "kind": "header_band_skipped",
        "table_row_index": table_row_index,
        "row_kind_hint": "ROW_HEADER_BAND",
        "semantic_lock_in": False,
        "mvp_input_provenance": _PROV_HINTS,
        "note": "002 J2-ROW; not final header classification",
    }


def _trace_note_candidate(table_row_index: int, row_kind_hint: str) -> dict[str, Any]:
    return {
        "trace_ref": f"mvp-note-candidate-{table_row_index}",
        "kind": "note_candidate",
        "table_row_index": table_row_index,
        "row_kind_hint": row_kind_hint,
        "semantic_lock_in": False,
        "mvp_input_provenance": _PROV_HINTS,
        "note": "002 J2-ROW; note row candidate not data body",
    }


def _trace_skipped_row_aggregate(table_row_index: int, row_kind_hint: str) -> dict[str, Any]:
    return {
        "trace_ref": f"mvp-skip-row-{table_row_index}",
        "kind": "skipped_row_candidate",
        "table_row_index": table_row_index,
        "row_kind_hint": row_kind_hint,
        "semantic_lock_in": False,
        "mvp_input_provenance": _PROV_HINTS,
        "note": "002 J2-ROW; aggregate row excluded from data rows",
    }


def _trace_cell_transcribed(
    *,
    table_row_index: int,
    table_column_index: int,
    logical_row_index: int,
) -> dict[str, Any]:
    return {
        "trace_ref": f"mvp-tx-r{table_row_index}c{table_column_index}",
        "kind": "cell_value_transcribed",
        "table_row_index": table_row_index,
        "table_column_index": table_column_index,
        "logical_row_index": logical_row_index,
        "values_key": f"c{table_column_index}",
        "semantic_lock_in": False,
        "mvp_input_provenance": _PROV_CELLS,
        "note": (
            "001 TableReadArtifact.cells raw_display transcribed; "
            "not typed normalization or measure semantics"
        ),
    }


def _trace_column_role_hint(
    *,
    table_column_index: int,
    column_role_hint: str,
    trace_kind: str,
    c_str: str,
) -> dict[str, Any]:
    return {
        "trace_ref": f"mvp-col-{trace_kind}-{c_str}",
        "kind": trace_kind,
        "table_column_index": table_column_index,
        "column_role_hint": column_role_hint,
        "semantic_lock_in": False,
        "mvp_input_provenance": _PROV_HINTS,
        "note": "002 J2-COL; not dimension/measure lock-in",
    }


def _build_mvp_column_slots(
    *,
    by_col: dict[str, str],
    rows: list[dict[str, Any]],
    trace_map: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    MVP ``column_slots[]``: **列カタログ / 参照面**（dimension・measure の意味確定ではない）。

    **Slot 集合（MVP 契約の正本）**:
    ``set(int(k) for k in by_column_index) ∪ 転記済み rows[].values の cN から復元した列 index``。
    **taxonomy_code には依存しない**。merges / multi-row header は未解決のまま（上位処理・trace / review へ）。

    - ``hint_from_002``: J2-COL の **候補**ラベル文字列を載せるだけ（確定ではない）。
    - ``trace_kind_preview`` / ``trace_ref_ids``: ``trace_map`` から拾った **説明用参照**（意味確定ではない）。
    """
    indices: set[int] = set()
    for k in by_col:
        try:
            indices.add(int(k))
        except (TypeError, ValueError):
            continue
    indices |= _table_column_indices_from_values_keys(rows)

    slots: list[dict[str, Any]] = []
    for ci in sorted(indices):
        kinds: list[str] = []
        refs: list[str] = []
        for t in trace_map:
            if not isinstance(t, dict):
                continue
            try:
                tic = t.get("table_column_index")
                if tic is None or int(tic) != ci:
                    continue
            except (TypeError, ValueError):
                continue
            kk = t.get("kind")
            if isinstance(kk, str) and kk not in kinds:
                kinds.append(kk)
            tr = t.get("trace_ref")
            if isinstance(tr, str) and tr and tr not in refs:
                refs.append(tr)
        kinds.sort()
        refs.sort()

        slot: dict[str, Any] = {
            "slot_id": f"col_{ci}",
            "table_column_index": ci,
            "values_key": f"c{ci}",
            "semantic_lock_in": False,
        }
        hk = by_col.get(str(ci))
        if hk is not None:
            slot["hint_from_002"] = hk
        if kinds:
            slot["trace_kind_preview"] = kinds
        if refs:
            slot["trace_ref_ids"] = refs
        slots.append(slot)
    return slots


def _mvp_build_rows_and_row_cell_traces(
    *,
    by_row_index: dict[str, str],
    row_indices: list[int],
    cell_src: dict[str, Any],
    trace_prefix: list[dict[str, Any]],
    row_index_enumeration_source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """
    ``rows[]`` と、行単位・セル転記の ``trace_map`` エントリを構築する。

    ``trace_prefix`` は行走査より前に前置される（例: TableScope レンジ fallback の説明 1 件）。

    Returns:
        (rows, trace_map_slice, skipped_row_trace_count, transcribed_cell_trace_count)
    """
    rows: list[dict[str, Any]] = []
    trace_map: list[dict[str, Any]] = list(trace_prefix)
    skipped = 0
    transcribed = 0

    fallback_unknown = not by_row_index

    for r in row_indices:
        if fallback_unknown:
            kind = "ROW_UNKNOWN"
        else:
            kind = by_row_index.get(str(r), "ROW_UNKNOWN")

        if kind == "ROW_HEADER_BAND":
            skipped += 1
            trace_map.append(_trace_header_band_skipped(r))
            continue
        if kind in ("ROW_NOTE", "ROW_NOTE_CANDIDATE"):
            skipped += 1
            trace_map.append(_trace_note_candidate(r, kind))
            continue
        if kind in _AGG_ROW_KINDS_SKIP_DATA:
            skipped += 1
            trace_map.append(_trace_skipped_row_aggregate(r, kind))
            continue

        logical_idx = len(rows)
        vals: dict[str, Any] = {}
        if cell_src:
            by_c = _sparse_cells_by_column_in_row(cell_src, r)
            for ci in sorted(by_c.keys()):
                cell = by_c[ci]
                raw = cell.get("raw_display")
                vals[f"c{ci}"] = "" if raw is None else str(raw)
                transcribed += 1
                trace_map.append(
                    _trace_cell_transcribed(
                        table_row_index=r,
                        table_column_index=ci,
                        logical_row_index=logical_idx,
                    )
                )
        rows.append(
            {
                "logical_row_index": logical_idx,
                "table_row_index": r,
                "values": vals,
                "mvp_stub": True,
                "normalization_hint": {
                    "from_002_row_kind": kind,
                    "semantic_lock_in": False,
                    "row_index_enumeration_source": row_index_enumeration_source,
                },
            }
        )

    return rows, trace_map, skipped, transcribed


def _mvp_trace_prefix_for_row_indices(
    *,
    by_row_index: dict[str, str],
    row_indices: list[int],
    table: Any | None,
) -> list[dict[str, Any]]:
    """``by_row_index`` が空でレンジ列挙したときだけ、fallback 由来の trace を 1 件前置する。"""
    if by_row_index or not row_indices:
        return []
    rm = getattr(table, "row_min", None) if table is not None else None
    rM = getattr(table, "row_max", None) if table is not None else None
    if rm is None or rM is None:
        return []
    return [_trace_row_index_table_scope_fallback(row_min=int(rm), row_max=int(rM))]


def _mvp_assert_003_assembly_invariants(
    rows: list[Any],
    trace_map: list[Any],
    column_slots: list[Any],
) -> None:
    """軽量な組立チェック（重いスキーマ検証はしない）。"""
    if not isinstance(rows, list):
        raise ValueError("003 MVP: rows must be a list")
    if not isinstance(trace_map, list):
        raise ValueError("003 MVP: trace_map must be a list")
    if not isinstance(column_slots, list):
        raise ValueError("003 MVP: column_slots must be a list")
    for r in rows:
        if not isinstance(r, dict):
            raise ValueError("003 MVP: each row must be a dict")
        for key in ("logical_row_index", "table_row_index", "values", "normalization_hint"):
            if key not in r:
                raise ValueError(f"003 MVP: row missing required key {key!r}")
        nh = r["normalization_hint"]
        if not isinstance(nh, dict):
            raise ValueError("003 MVP: normalization_hint must be a dict")
        if nh.get("semantic_lock_in") is not False:
            raise ValueError("003 MVP: row normalization_hint.semantic_lock_in must be False")
    for t in trace_map:
        if not isinstance(t, dict):
            raise ValueError("003 MVP: each trace_map entry must be a dict")
        if "semantic_lock_in" in t and t.get("semantic_lock_in") is not False:
            raise ValueError("003 MVP: trace_map semantic_lock_in must be False when present")
    for s in column_slots:
        if not isinstance(s, dict):
            raise ValueError("003 MVP: each column_slots entry must be a dict")
        if s.get("semantic_lock_in") is not False:
            raise ValueError("003 MVP: column_slots semantic_lock_in must be False")


def _mvp_append_column_role_traces(
    trace_map: list[dict[str, Any]],
    by_column_index: dict[str, str],
) -> None:
    """J2-COL 由来の列ロール候補を ``trace_map`` に追加（意味確定ではない）。"""
    for c_str in sorted(by_column_index.keys(), key=lambda x: int(x)):
        ckind = by_column_index[c_str]
        ci = int(c_str)
        if ckind in ("COL_ATTRIBUTE", "COL_ATTRIBUTE_CANDIDATE"):
            tkind = "attribute_column_candidate"
        elif ckind in ("COL_MEASURE", "COL_MEASURE_CANDIDATE"):
            tkind = "measure_column_candidate"
        else:
            tkind = "column_role_hint"
        trace_map.append(
            _trace_column_role_hint(
                table_column_index=ci,
                column_role_hint=ckind,
                trace_kind=tkind,
                c_str=c_str,
            )
        )


def _mvp_build_normalization_stub_meta(
    *,
    data_row_count: int,
    skipped_row_trace_count: int,
    column_hint_trace_count: int,
    transcribed_cell_trace_count: int,
    column_slot_count: int,
) -> dict[str, Any]:
    return {
        "schema_ref": MVP_NORMALIZATION_STUB_SCHEMA_REF,
        "column_slots_schema_ref": MVP_COLUMN_SLOTS_SCHEMA_REF,
        "data_row_count": data_row_count,
        "skipped_row_trace_count": skipped_row_trace_count,
        "column_hint_trace_count": column_hint_trace_count,
        "transcribed_cell_trace_count": transcribed_cell_trace_count,
        "column_slot_count": column_slot_count,
    }


def extract_normalization_input_hints_from_judgment_evidence(
    evidence: list[Any] | None,
) -> dict[str, Any] | None:
    """
    ``evidence[]`` から J2-ROW / J2-COL の ``details`` を集約し、
    ``NormalizedDataset.dataset_payload`` 用のヒント dict を返す。

    該当が無ければ ``None``。
    """
    if not evidence:
        return None
    by_row: dict[str, str] | None = None
    by_col: dict[str, str] | None = None
    primary_labels_schema: str | None = None
    intent: str | None = None

    for item in evidence:
        if not isinstance(item, dict):
            continue
        rid = item.get("rule_id")
        details = item.get("details")
        if not isinstance(details, dict):
            continue
        if primary_labels_schema is None:
            primary_labels_schema = details.get("primary_labels_schema")
        if intent is None:
            intent = details.get("intent")
        if rid == RULE_J2_ROW:
            br = details.get("by_row_index")
            if isinstance(br, dict):
                by_row = {str(k): str(v) for k, v in br.items()}
        elif rid == RULE_J2_COL:
            bc = details.get("by_column_index")
            if isinstance(bc, dict):
                by_col = {str(k): str(v) for k, v in bc.items()}

    if by_row is None and by_col is None:
        return None

    return {
        "schema_ref": NORMALIZATION_HINTS_SCHEMA_REF,
        "source": "002_judgment_evidence",
        "intent": intent
        or "normalization_input_hints_not_semantic_lock_in",
        "rule_ids": [RULE_J2_ROW, RULE_J2_COL],
        "primary_labels_schema": primary_labels_schema,
        "by_row_index": by_row or {},
        "by_column_index": by_col or {},
    }


def merge_hints_into_dataset_payload(
    payload: dict[str, Any],
    hints: dict[str, Any],
) -> dict[str, Any]:
    """既存 ``dataset_payload`` を壊さず ``normalization_input_hints`` を上書きマージ。"""
    out = dict(payload)
    out["normalization_input_hints"] = hints
    return out


def read_normalization_input_hints_from_dataset_payload(
    dataset_payload: dict[str, Any],
) -> dict[str, Any] | None:
    """
    ``dataset_payload.normalization_input_hints`` を返す（002 ``JudgmentResult.evidence``
    由来で materialize が載せたオブジェクトを 003 スタブが読む入口）。
    """
    h = dataset_payload.get("normalization_input_hints")
    return h if isinstance(h, dict) else None


def build_mvp_rows_and_trace_map_from_hints(
    hints: dict[str, Any],
    *,
    table: Any | None = None,
    cells: dict[str, Any] | None = None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
]:
    """
    ``normalization_input_hints`` を読み、MVP 用の ``rows[]`` / ``trace_map`` / ``column_slots[]`` を生成する。

    - 行: ``ROW_HEADER_BAND`` → ``header_band_skipped``。``ROW_NOTE`` / ``ROW_NOTE_CANDIDATE`` → ``note_candidate``。
      集計行は ``skipped_row_candidate``。
    - 列: ``COL_ATTRIBUTE`` / ``COL_ATTRIBUTE_CANDIDATE`` → ``attribute_column_candidate``。
      ``COL_MEASURE`` / ``COL_MEASURE_CANDIDATE`` → ``measure_column_candidate``。その他は ``column_role_hint``。
    - データ行: ``cells`` があれば同じ ``table_row_index`` の 001 観測を ``values[\"c{N}\"]`` に **転記**（型確定・意味確定ではない）。
    - ``column_slots``: **契約どおり** ``by_column_index`` の列キーと ``rows[].values`` の ``cN`` 列の**和集合**（taxonomy 非依存）。
      **``values`` のキーは当面 ``cN`` のまま**（論理列 ID への置換はしない）。
    いずれも **004 dimensions/measures 確定ではない**（``semantic_lock_in: false``）。
    """
    by_row, by_col = _mvp_coerce_row_column_maps(hints)
    row_indices = _mvp_resolve_table_row_indices(by_row_index=by_row, table=table)
    cell_src = cells if isinstance(cells, dict) else {}
    trace_prefix = _mvp_trace_prefix_for_row_indices(
        by_row_index=by_row, row_indices=row_indices, table=table
    )
    row_index_enumeration_source = (
        _ROW_ENUM_FROM_HINT_KEYS if by_row else _PROV_TABLE_SCOPE_FALLBACK
    )

    rows, trace_map, skipped, transcribed = _mvp_build_rows_and_row_cell_traces(
        by_row_index=by_row,
        row_indices=row_indices,
        cell_src=cell_src,
        trace_prefix=trace_prefix,
        row_index_enumeration_source=row_index_enumeration_source,
    )
    _mvp_append_column_role_traces(trace_map, by_col)

    column_slots = _build_mvp_column_slots(by_col=by_col, rows=rows, trace_map=trace_map)
    meta = _mvp_build_normalization_stub_meta(
        data_row_count=len(rows),
        skipped_row_trace_count=skipped,
        column_hint_trace_count=len(by_col),
        transcribed_cell_trace_count=transcribed,
        column_slot_count=len(column_slots),
    )
    _mvp_assert_003_assembly_invariants(rows, trace_map, column_slots)
    return rows, trace_map, meta, column_slots


def assemble_mvp_003_dataset_payload_artifacts(
    hints: dict[str, Any],
    *,
    table: Any | None = None,
    cells: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """
    003 MVP の ``rows`` / ``trace_map`` / ``mvp_normalization_stub`` / ``column_slots`` を一括生成。

    ``build_mvp_rows_and_trace_map_from_hints`` のエイリアス（services 側で「003 組立」として明示するため）。
    """
    return build_mvp_rows_and_trace_map_from_hints(hints, table=table, cells=cells)
