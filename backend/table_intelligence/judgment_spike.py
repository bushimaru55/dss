"""
002 判定スパイク（P0 健全性・parse_warnings 連携・薄い J2-TAX・行／列一次ラベル候補）。

本番の全ルールエンジンではなく、SPEC-TI-002 / 006 に沿った根拠付き JudgmentResult 生成。
011 の数値評価・004 の意味確定は含めない。行／列ラベルは **003 入力候補**であり dimensions/measures ではない。
"""

from __future__ import annotations

import re
from typing import Any

from table_intelligence.models import (
    JudgmentDecision,
    TableScope,
    TI_TABLE_CROSSTAB,
    TI_TABLE_FORM_REPORT,
    TI_TABLE_KEY_VALUE,
    TI_TABLE_LIST_DETAIL,
    TI_TABLE_LOOKUP_MATRIX,
    TI_TABLE_PIVOT_LIKE,
    TI_TABLE_TIME_SERIES,
    TI_TABLE_UNKNOWN,
)

# 再現性説明用（006 MINOR の judge_profile_id に相当する識別子を details に載せる）
JUDGE_PROFILE_SPIKE = "ti.judge.spike.v1"
"""009 必須軸ゲートを J2-TAX-001 に取り込んだ版。"""

# J2-ROW / J2-COL の evidence.details スキーマ識別子（003 が参照しうる）
PRIMARY_LABELS_SCHEMA = "ti.judgment.primary_labels.v1"

# SPEC-TI-002 §行種別 / §列種別（暫定 enum の文字列値）
ROW_DETAIL = "ROW_DETAIL"
ROW_SUBTOTAL = "ROW_SUBTOTAL"
ROW_GRAND_TOTAL = "ROW_GRAND_TOTAL"
ROW_NOTE = "ROW_NOTE"
ROW_NOTE_CANDIDATE = "ROW_NOTE_CANDIDATE"  # 003 向け候補（確定の注記行ではない）
ROW_HEADER_BAND = "ROW_HEADER_BAND"
ROW_UNKNOWN = "ROW_UNKNOWN"

COL_ATTRIBUTE = "COL_ATTRIBUTE"
COL_ATTRIBUTE_CANDIDATE = "COL_ATTRIBUTE_CANDIDATE"
COL_MEASURE = "COL_MEASURE"
COL_MEASURE_CANDIDATE = "COL_MEASURE_CANDIDATE"
COL_TIME = "COL_TIME"
COL_UNIT = "COL_UNIT"
COL_NOTE = "COL_NOTE"
COL_UNKNOWN = "COL_UNKNOWN"

# 001 / 012 接続前提の「致命的」読取警告（P0 で REJECT に寄せる最小集合）
FATAL_PARSE_WARNING_CODES: frozenset[str] = frozenset(
    {
        "TI_READ_NO_TABLE_CANDIDATE",
        "TI_READ_ARTIFACT_INVALID",
        "TI_READ_BBOX_INVALID",
    }
)

_NUMERIC_RE = re.compile(r"^[\d,.\s%-]+$")
_DATE_LIKE_RE = re.compile(
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|Q[1-4][\s/-]?\d{4}|\d{4}年)"
)
_PIVOT_KW_RE = re.compile(
    r"(小計|合計|総計|計|Subtotal|Grand\s*Total|Total)",
    re.IGNORECASE,
)
_SUBTOTAL_KW_RE = re.compile(r"(小計|Subtotal)", re.IGNORECASE)
_GRAND_KW_RE = re.compile(r"(合計|総計|Grand\s*Total|Grand\s*計)", re.IGNORECASE)
_UNIT_HEADER_RE = re.compile(r"(単位|円|\(千円\)|\(百万\)|%|‰)")
_NOTE_COL_RE = re.compile(r"(備考|注記|説明|Notes?)", re.IGNORECASE)


def _bbox_targets(table: TableScope) -> list[dict[str, int]]:
    if (
        table.row_min is None
        or table.col_min is None
        or table.row_max is None
        or table.col_max is None
    ):
        return []
    return [
        {
            "row_min": table.row_min,
            "row_max": table.row_max,
            "column_min": table.col_min,
            "column_max": table.col_max,
        }
    ]


def _iter_cell_rc(cells: dict[str, Any]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for key, val in cells.items():
        if isinstance(val, dict) and "r" in val and "c" in val:
            try:
                out.append((int(val["r"]), int(val["c"])))
            except (TypeError, ValueError):
                continue
            continue
        m = re.match(r"^R(\d+)C(\d+)$", key)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def _collect_p0_failures(
    table: TableScope,
    cells: dict[str, Any],
    parse_warnings: list[Any],
) -> list[dict[str, Any]]:
    """P0 違反ごとに evidence 1 要素分（rule_id / conclusion / targets / refs_parse_warnings / details）。"""
    failures: list[dict[str, Any]] = []
    targets = _bbox_targets(table)

    if not cells:
        failures.append(
            {
                "rule_id": "J2-P0-001",
                "conclusion": "REJECT: sparse cells empty; no observable grid",
                "targets": targets,
                "refs_parse_warnings": [],
                "details": {
                    "judge_profile_id": JUDGE_PROFILE_SPIKE,
                    "p0_code": "EMPTY_CELLS",
                },
            }
        )
        return failures

    if (
        table.row_min is not None
        and table.row_max is not None
        and table.row_max < table.row_min
    ) or (
        table.col_min is not None
        and table.col_max is not None
        and table.col_max < table.col_min
    ):
        failures.append(
            {
                "rule_id": "J2-P0-002",
                "conclusion": "REJECT: TableScope bbox inverted (row_max<row_min or col_max<col_min)",
                "targets": targets,
                "refs_parse_warnings": [],
                "details": {
                    "judge_profile_id": JUDGE_PROFILE_SPIKE,
                    "p0_code": "BBOX_INVERTED",
                    "row_min": table.row_min,
                    "row_max": table.row_max,
                    "col_min": table.col_min,
                    "col_max": table.col_max,
                },
            }
        )

    if (
        table.row_min is not None
        and table.row_max is not None
        and table.col_min is not None
        and table.col_max is not None
    ):
        outside: list[dict[str, int]] = []
        for r, c in _iter_cell_rc(cells):
            if not (
                table.row_min <= r <= table.row_max
                and table.col_min <= c <= table.col_max
            ):
                outside.append({"r": r, "c": c})
        if outside:
            failures.append(
                {
                    "rule_id": "J2-P0-003",
                    "conclusion": "REJECT: at least one cell falls outside TableScope bbox",
                    "targets": targets + outside[:8],
                    "refs_parse_warnings": [],
                    "details": {
                        "judge_profile_id": JUDGE_PROFILE_SPIKE,
                        "p0_code": "CELL_OUTSIDE_BBOX",
                        "outside_sample": outside[:16],
                        "outside_count": len(outside),
                    },
                }
            )

    fatal_idx: list[int] = []
    for i, w in enumerate(parse_warnings):
        if not isinstance(w, dict):
            continue
        code = w.get("code")
        sev = (w.get("severity") or "").lower()
        if sev == "error" or (
            isinstance(code, str) and code in FATAL_PARSE_WARNING_CODES
        ):
            fatal_idx.append(i)
    if fatal_idx:
        failures.append(
            {
                "rule_id": "J2-P0-004",
                "conclusion": "REJECT: fatal parse_warning (severity=error or fatal code)",
                "targets": targets,
                "refs_parse_warnings": fatal_idx,
                "details": {
                    "judge_profile_id": JUDGE_PROFILE_SPIKE,
                    "p0_code": "FATAL_PARSE_WARNING",
                },
            }
        )

    return failures


def _warning_evidence(parse_warnings: list[Any]) -> dict[str, Any] | None:
    if not parse_warnings:
        return None
    indices = list(range(len(parse_warnings)))
    return {
        "rule_id": "J2-WARN-001",
        "conclusion": "001 parse_warnings present; downstream review signals attached",
        "targets": [],
        "refs_parse_warnings": indices,
        "details": {
            "judge_profile_id": JUDGE_PROFILE_SPIKE,
            "warning_count": len(parse_warnings),
        },
    }


def _cell_stats(cells: dict[str, Any]) -> dict[str, Any]:
    numeric = 0
    date_like = 0
    textish = 0
    total = 0
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        total += 1
        raw = str(val.get("raw_display") or "")
        s = raw.strip()
        if not s:
            continue
        if _DATE_LIKE_RE.search(s):
            date_like += 1
        elif _NUMERIC_RE.match(s) and any(ch.isdigit() for ch in s):
            numeric += 1
        else:
            textish += 1
    return {
        "cell_count": total,
        "numeric_like_count": numeric,
        "date_like_count": date_like,
        "text_like_count": textish,
    }


def _effective_bbox_corners(
    table: TableScope, max_r: int, max_c: int
) -> tuple[int, int, int, int]:
    """bbox 未定義時は稀疏セル包みの 0..max を仮定。"""
    if (
        table.row_min is not None
        and table.row_max is not None
        and table.col_min is not None
        and table.col_max is not None
    ):
        return table.row_min, table.col_min, table.row_max, table.col_max
    return 0, 0, max_r, max_c


def _left_stub_text_ratio(
    cells: dict[str, Any], col_min: int, row_min: int, row_max: int
) -> float:
    """左端列の、見出し行より下のセルにテキストがある割合（009 一覧・左端見出しの代理）。"""
    texts = 0
    total = 0
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            r = int(val["r"])
            c = int(val["c"])
        except (KeyError, TypeError, ValueError):
            continue
        if c != col_min or r <= row_min:
            continue
        total += 1
        raw = str(val.get("raw_display") or "").strip()
        if raw and not (
            _NUMERIC_RE.match(raw) and any(ch.isdigit() for ch in raw)
        ):
            texts += 1
    if total == 0:
        return 0.0
    return texts / total


def _distinct_labels_in_column(
    cells: dict[str, Any], col: int, row_min: int, row_max: int, *, skip_row: int | None
) -> int:
    seen: set[str] = set()
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            r = int(val["r"])
            c = int(val["c"])
        except (KeyError, TypeError, ValueError):
            continue
        if c != col or r < row_min or r > row_max:
            continue
        if skip_row is not None and r == skip_row:
            continue
        raw = str(val.get("raw_display") or "").strip()
        if raw:
            seen.add(raw[:128])
    return len(seen)


def _distinct_labels_in_row(
    cells: dict[str, Any], row: int, col_min: int, col_max: int, *, skip_col: int | None
) -> int:
    seen: set[str] = set()
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            r = int(val["r"])
            c = int(val["c"])
        except (KeyError, TypeError, ValueError):
            continue
        if r != row or c < col_min or c > col_max:
            continue
        if skip_col is not None and c == skip_col:
            continue
        raw = str(val.get("raw_display") or "").strip()
        if raw:
            seen.add(raw[:128])
    return len(seen)


def _interior_numeric_count(
    cells: dict[str, Any],
    row_min: int,
    col_min: int,
    row_max: int,
    col_max: int,
) -> int:
    """交差部（行見出し・列見出し帯を除く）の数値セル数。クロス表の「度量」代理。"""
    n = 0
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            r = int(val["r"])
            c = int(val["c"])
        except (KeyError, TypeError, ValueError):
            continue
        if r <= row_min or c <= col_min:
            continue
        if r > row_max or c > col_max:
            continue
        raw = str(val.get("raw_display") or "").strip()
        if raw and _NUMERIC_RE.match(raw) and any(ch.isdigit() for ch in raw):
            n += 1
    return n


def _date_fraction_in_row(
    cells: dict[str, Any], row: int, col_min: int, col_max: int
) -> float:
    total = 0
    hits = 0
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            r = int(val["r"])
            c = int(val["c"])
        except (KeyError, TypeError, ValueError):
            continue
        if r != row or c < col_min or c > col_max:
            continue
        total += 1
        raw = str(val.get("raw_display") or "").strip()
        if raw and _DATE_LIKE_RE.search(raw):
            hits += 1
    if total == 0:
        return 0.0
    return hits / total


def _pivot_keyword_hits(cells: dict[str, Any]) -> int:
    n = 0
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        raw = str(val.get("raw_display") or "")
        if _PIVOT_KW_RE.search(raw):
            n += 1
    return n


def _grid_fill_ratio(
    n_rows: int, n_cols: int, cell_count: int, merge_count: int
) -> float:
    area = max(n_rows * n_cols, 1)
    # 結合は格子の疎性の代理指標として軽く加味
    return min(1.0, (cell_count + merge_count * 0.5) / area)


def _header_row_score(cells: dict[str, Any], row_min: int | None) -> float:
    if row_min is None:
        return 0.0
    header_cells = 0
    data_cells = 0
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            r = int(val["r"])
        except (KeyError, TypeError, ValueError):
            continue
        if r != row_min:
            continue
        raw = str(val.get("raw_display") or "").strip()
        if not raw:
            continue
        if _NUMERIC_RE.match(raw) and any(ch.isdigit() for ch in raw):
            data_cells += 1
        else:
            header_cells += 1
    if header_cells + data_cells == 0:
        return 0.0
    return header_cells / (header_cells + data_cells)


def _taxonomy_009_axis_gates(
    code: str, obs: dict[str, Any]
) -> tuple[bool, list[str]]:
    """
    009 各型の「必須軸」を、001 観測だけで検査できる最小集合として検証する。

    満たさない場合は候補から外し、UNKNOWN または別候補へ寄せる前提。
    """
    reasons: list[str] = []
    if code == TI_TABLE_LIST_DETAIL:
        if obs["n_rows"] < 2:
            reasons.append("axis_rows_lt_2")
        if obs["n_cols"] < 2:
            reasons.append("axis_cols_lt_2")
        if not (
            obs["header_row_text_ratio"] >= 0.12
            or obs["left_stub_text_ratio"] >= 0.12
            or obs["numeric_ratio"] >= 0.18
        ):
            reasons.append("no_header_stub_or_measure_signal")
        return not reasons, reasons

    if code == TI_TABLE_CROSSTAB:
        if obs["n_rows"] < 3:
            reasons.append("need_row_axis_depth_3")
        if obs["n_cols"] < 3:
            reasons.append("need_col_axis_depth_3")
        if obs["distinct_row_labels_stub"] < 2:
            reasons.append("row_axis_labels_lt_2")
        if obs["distinct_col_labels_header"] < 2:
            reasons.append("col_axis_labels_lt_2")
        if obs["interior_numeric_count"] < 1:
            reasons.append("interior_measure_absent")
        return not reasons, reasons

    if code == TI_TABLE_TIME_SERIES:
        if obs["n_cols"] < 4:
            reasons.append("time_columns_need_width_4")
        if obs["date_fraction_header_row"] < 0.12 and obs["date_like_ratio"] < 0.12:
            reasons.append("time_axis_on_columns_not_evident")
        return not reasons, reasons

    if code == TI_TABLE_KEY_VALUE:
        if obs["n_cols"] > 3:
            reasons.append("too_wide_for_key_value_stack")
        if obs["n_rows"] < 2:
            reasons.append("need_vertical_stack_depth_2")
        return not reasons, reasons

    if code == TI_TABLE_LOOKUP_MATRIX:
        if obs["numeric_ratio"] > 0.28:
            reasons.append("numeric_not_subordinate")
        if obs["n_rows"] < 2 or obs["n_cols"] < 2:
            reasons.append("matrix_shape_too_shallow")
        return not reasons, reasons

    if code == TI_TABLE_FORM_REPORT:
        if obs["merge_count"] < 2 and obs["grid_fill_ratio"] >= 0.22:
            reasons.append("regular_grid_not_weak_layout")
        return not reasons, reasons

    if code == TI_TABLE_PIVOT_LIKE:
        if obs["pivot_keyword_hits"] < 1:
            reasons.append("subtotal_grand_total_keywords_absent")
        return not reasons, reasons

    return True, []


def _thin_taxonomy(
    table: TableScope, cells: dict[str, Any], merges_list: list[Any]
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """
    観測特徴＋009 必須軸ゲートから単一 taxonomy_code を返す。

    ヒューリスティクスで仮決め → 009 軸ゲート不通過なら ``TI_TABLE_UNKNOWN`` に落とし、
    ``details.taxonomy_009`` に観測と失敗理由を残す。
    """
    stats = _cell_stats(cells)
    rc = _iter_cell_rc(cells)
    max_r = max((r for r, _ in rc), default=0)
    max_c = max((c for _, c in rc), default=0)
    row_min, col_min, row_max, col_max = _effective_bbox_corners(table, max_r, max_c)
    n_rows = row_max - row_min + 1
    n_cols = col_max - col_min + 1

    total = stats["cell_count"] or 1
    numeric_ratio = stats["numeric_like_count"] / total
    date_ratio = stats["date_like_count"] / total
    hdr = _header_row_score(cells, row_min)
    left_stub = _left_stub_text_ratio(cells, col_min, row_min, row_max)
    interior_n = _interior_numeric_count(cells, row_min, col_min, row_max, col_max)
    dr_stub = _distinct_labels_in_column(
        cells, col_min, row_min, row_max, skip_row=row_min
    )
    dc_hdr = _distinct_labels_in_row(
        cells, row_min, col_min, col_max, skip_col=col_min
    )
    dfh = _date_fraction_in_row(cells, row_min, col_min, col_max)
    merge_count = len(merges_list)
    fill = _grid_fill_ratio(n_rows, n_cols, stats["cell_count"], merge_count)
    pkhits = _pivot_keyword_hits(cells)

    obs: dict[str, Any] = {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "numeric_ratio": round(numeric_ratio, 4),
        "date_like_ratio": round(date_ratio, 4),
        "header_row_text_ratio": round(hdr, 4),
        "left_stub_text_ratio": round(left_stub, 4),
        "interior_numeric_count": interior_n,
        "distinct_row_labels_stub": dr_stub,
        "distinct_col_labels_header": dc_hdr,
        "date_fraction_header_row": round(dfh, 4),
        "merge_count": merge_count,
        "grid_fill_ratio": round(fill, 4),
        "pivot_keyword_hits": pkhits,
        "cell_count": stats["cell_count"],
    }

    features: dict[str, Any] = {
        "judge_profile_id": JUDGE_PROFILE_SPIKE,
        "taxonomy_schema_ref": "SPEC-TI-009-0.1",
        "grid_rows": n_rows,
        "grid_cols": n_cols,
        "max_r": max_r,
        "max_c": max_c,
        "numeric_ratio": obs["numeric_ratio"],
        "date_like_ratio": obs["date_like_ratio"],
        "header_row_text_ratio": obs["header_row_text_ratio"],
        "left_stub_text_ratio": obs["left_stub_text_ratio"],
        "taxonomy_009": {
            "axes_observed": {
                "row_axis_labels_stub_distinct": dr_stub,
                "col_axis_labels_header_distinct": dc_hdr,
                "matrix_interior_numeric_cells": interior_n,
                "time_axis_on_columns_score": obs["date_fraction_header_row"],
                "layout_weak_by_merge_or_fill": merge_count >= 2 or fill < 0.22,
                "pivot_subtotal_like_labels": pkhits,
            },
        },
    }

    alternates: list[dict[str, Any]] = []
    heuristic_primary: str | None = None
    heuristic_alts: list[dict[str, Any]] = []

    # --- 仮分類（v0 と同型の極薄ルール）---
    if n_rows <= 2 and n_cols >= 2:
        heuristic_primary = TI_TABLE_KEY_VALUE
        heuristic_alts = [
            {"code": TI_TABLE_LIST_DETAIL, "rationale": "wide short grid could be list"}
        ]
    elif n_cols >= 6 and n_rows <= 4 and (date_ratio >= 0.15 or hdr >= 0.4):
        heuristic_primary = TI_TABLE_TIME_SERIES
        heuristic_alts = [
            {"code": TI_TABLE_CROSSTAB, "rationale": "many columns; verify axis semantics"}
        ]
    elif n_rows >= 3 and n_cols >= 3 and numeric_ratio >= 0.25:
        heuristic_primary = TI_TABLE_CROSSTAB
        heuristic_alts = [
            {"code": TI_TABLE_LIST_DETAIL, "rationale": "could be tall list with measures"},
            {"code": TI_TABLE_LOOKUP_MATRIX, "rationale": "if symbols dominate reclassify"},
        ]
    elif n_rows >= 4 and n_cols >= 2 and hdr >= 0.3:
        heuristic_primary = TI_TABLE_LIST_DETAIL
        heuristic_alts = [
            {"code": TI_TABLE_FORM_REPORT, "rationale": "irregular layout not ruled out"}
        ]
    else:
        heuristic_primary = TI_TABLE_UNKNOWN
        heuristic_alts = [
            {"code": TI_TABLE_LIST_DETAIL, "rationale": "default business-table hypothesis"},
            {"code": TI_TABLE_FORM_REPORT, "rationale": "weak grid / sparse read"},
        ]

    assert heuristic_primary is not None

    ok, fail_reasons = _taxonomy_009_axis_gates(heuristic_primary, obs)
    features["taxonomy_009"]["heuristic_primary"] = heuristic_primary
    features["taxonomy_009"]["axis_gates_passed"] = ok
    if ok:
        features["taxonomy_009"]["axis_gate_failures"] = []
        alternates = list(heuristic_alts)
        if heuristic_primary == TI_TABLE_UNKNOWN:
            features["alternate_taxonomies"] = heuristic_alts
        return heuristic_primary, alternates, features

    features["taxonomy_009"]["axis_gate_failures"] = fail_reasons
    # ゲート再試行: 代替候補のうち最初に通るものを採用
    for alt in heuristic_alts:
        acode = alt["code"]
        ok2, _ = _taxonomy_009_axis_gates(acode, obs)
        if ok2:
            features["taxonomy_009"]["promoted_from_heuristic"] = {
                "from": heuristic_primary,
                "to": acode,
                "reason": "primary_failed_009_axis_gate",
            }
            al2 = [a for a in heuristic_alts if a["code"] != acode] + [
                {
                    "code": heuristic_primary,
                    "rationale": "heuristic failed 009 axis gate",
                }
            ]
            return acode, al2, features

    # LIST_DETAIL は比較的緩いゲート → 最後のフォールバック候補
    ok_ld, _ = _taxonomy_009_axis_gates(TI_TABLE_LIST_DETAIL, obs)
    if ok_ld and heuristic_primary != TI_TABLE_LIST_DETAIL:
        features["taxonomy_009"]["promoted_from_heuristic"] = {
            "from": heuristic_primary,
            "to": TI_TABLE_LIST_DETAIL,
            "reason": "fallback_list_detail_after_gate_failure",
        }
        return TI_TABLE_LIST_DETAIL, [
            {"code": heuristic_primary, "rationale": "failed 009 gates; weak fallback"},
            *heuristic_alts,
        ], features

    features["alternate_taxonomies"] = [
        {"code": heuristic_primary, "rationale": "heuristic; failed 009 axis gates"},
        *heuristic_alts,
    ]
    return TI_TABLE_UNKNOWN, features["alternate_taxonomies"], features


def _cell_at(cells: dict[str, Any], r: int, c: int) -> dict[str, Any] | None:
    key = f"R{r}C{c}"
    v = cells.get(key)
    if isinstance(v, dict):
        return v
    for val in cells.values():
        if not isinstance(val, dict):
            continue
        try:
            if int(val["r"]) == r and int(val["c"]) == c:
                return val
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _row_joined_text(
    cells: dict[str, Any], r: int, col_min: int, col_max: int
) -> str:
    parts: list[str] = []
    for c in range(col_min, col_max + 1):
        v = _cell_at(cells, r, c)
        if v is None:
            continue
        raw = str(v.get("raw_display") or "").strip()
        if raw:
            parts.append(raw)
    return " ".join(parts)


def _row_has_any_cell(
    cells: dict[str, Any], r: int, col_min: int, col_max: int
) -> bool:
    for c in range(col_min, col_max + 1):
        v = _cell_at(cells, r, c)
        if v is None:
            continue
        if str(v.get("raw_display") or "").strip():
            return True
    return False


def _header_row_text_fraction(
    cells: dict[str, Any], row_min: int, col_min: int, col_max: int
) -> float:
    texts = 0
    total = 0
    for c in range(col_min, col_max + 1):
        v = _cell_at(cells, row_min, c)
        if v is None:
            continue
        raw = str(v.get("raw_display") or "").strip()
        if not raw:
            continue
        total += 1
        if _NUMERIC_RE.match(raw) and any(ch.isdigit() for ch in raw):
            continue
        texts += 1
    if total == 0:
        return 0.0
    return texts / total


def _infer_primary_row_labels(
    cells: dict[str, Any],
    row_min: int,
    col_min: int,
    row_max: int,
    col_max: int,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in range(row_min, row_max + 1):
        if not _row_has_any_cell(cells, r, col_min, col_max):
            out[str(r)] = ROW_UNKNOWN
            continue
        joined = _row_joined_text(cells, r, col_min, col_max)
        if _SUBTOTAL_KW_RE.search(joined):
            out[str(r)] = ROW_SUBTOTAL
            continue
        if _GRAND_KW_RE.search(joined) and r == row_max:
            out[str(r)] = ROW_GRAND_TOTAL
            continue
        if r == row_min:
            out[str(r)] = (
                ROW_HEADER_BAND
                if _header_row_text_fraction(cells, row_min, col_min, col_max)
                >= 0.35
                else ROW_DETAIL
            )
            continue
        if r == row_max and len(joined) >= 20 and not any(
            ch.isdigit() for ch in joined[:40]
        ):
            out[str(r)] = ROW_NOTE_CANDIDATE
            continue
        out[str(r)] = ROW_DETAIL
    return out


def _infer_primary_col_labels(
    cells: dict[str, Any],
    row_min: int,
    col_min: int,
    row_max: int,
    col_max: int,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in range(col_min, col_max + 1):
        col_observed = False
        for r in range(row_min, row_max + 1):
            v = _cell_at(cells, r, c)
            if v is not None and str(v.get("raw_display") or "").strip():
                col_observed = True
                break
        if not col_observed:
            out[str(c)] = COL_UNKNOWN
            continue
        if c == col_min:
            out[str(c)] = COL_ATTRIBUTE_CANDIDATE
            continue
        h = _cell_at(cells, row_min, c)
        hraw = str(h.get("raw_display") or "").strip() if h else ""
        if hraw and _DATE_LIKE_RE.search(hraw):
            out[str(c)] = COL_TIME
            continue
        if hraw and _UNIT_HEADER_RE.search(hraw):
            out[str(c)] = COL_UNIT
            continue
        if hraw and _NOTE_COL_RE.search(hraw):
            out[str(c)] = COL_NOTE
            continue
        nums = 0
        total = 0
        for r in range(row_min + 1, row_max + 1):
            v = _cell_at(cells, r, c)
            if v is None:
                continue
            raw = str(v.get("raw_display") or "").strip()
            if not raw:
                continue
            total += 1
            if _NUMERIC_RE.match(raw) and any(ch.isdigit() for ch in raw):
                nums += 1
        if total >= 1 and nums / total >= 0.55:
            out[str(c)] = COL_MEASURE_CANDIDATE
            continue
        if c == col_max and total >= 1:
            textish = 0
            for r in range(row_min + 1, row_max + 1):
                v = _cell_at(cells, r, c)
                if v is None:
                    continue
                raw = str(v.get("raw_display") or "").strip()
                if raw and not (
                    _NUMERIC_RE.match(raw) and any(ch.isdigit() for ch in raw)
                ):
                    textish += 1
            if textish >= max(1, total // 2):
                out[str(c)] = COL_NOTE
                continue
        out[str(c)] = COL_UNKNOWN
    return out


def _row_col_primary_evidence(
    table: TableScope,
    cells: dict[str, Any],
    row_min: int,
    col_min: int,
    row_max: int,
    col_max: int,
) -> list[dict[str, Any]]:
    """J2-ROW-001 / J2-COL-001: 003 が参照しうる一次ラベル候補（確定の dimension/measure ではない）。"""
    by_row = _infer_primary_row_labels(cells, row_min, col_min, row_max, col_max)
    by_col = _infer_primary_col_labels(cells, row_min, col_min, row_max, col_max)
    base = {
        "judge_profile_id": JUDGE_PROFILE_SPIKE,
        "primary_labels_schema": PRIMARY_LABELS_SCHEMA,
        "coordinate_space": "0-based inclusive cell indices (001)",
        "intent": "normalization_input_hints_not_semantic_lock_in",
    }
    return [
        {
            "rule_id": "J2-ROW-001",
            "conclusion": "primary row-kind candidates keyed by row index (003 input)",
            "targets": _bbox_targets(table),
            "refs_parse_warnings": [],
            "details": {
                **base,
                "by_row_index": by_row,
            },
        },
        {
            "rule_id": "J2-COL-001",
            "conclusion": "primary column-role candidates keyed by column index (003 input)",
            "targets": _bbox_targets(table),
            "refs_parse_warnings": [],
            "details": {
                **base,
                "by_column_index": by_col,
            },
        },
    ]


def build_judgment_from_read_observation(
    table: TableScope,
    cells: dict[str, Any],
    merges: list[Any],
    parse_warnings: list[Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    """
    TableReadArtifact 観測と TableScope から decision / taxonomy_code / evidence[] を生成する。

    Returns:
        (decision, taxonomy_code, evidence) — evidence は非空。
    """
    pw = parse_warnings if isinstance(parse_warnings, list) else []
    merges_list = merges if isinstance(merges, list) else []

    p0_items = _collect_p0_failures(table, cells, pw)
    evidence: list[dict[str, Any]] = []

    if p0_items:
        evidence.extend(p0_items)
        w_ev = _warning_evidence(pw)
        if w_ev:
            evidence.append(w_ev)
        tax_ev: dict[str, Any] = {
            "rule_id": "J2-TAX-000",
            "conclusion": "taxonomy not classified due to P0 failure",
            "targets": _bbox_targets(table),
            "refs_parse_warnings": [],
            "details": {
                "judge_profile_id": JUDGE_PROFILE_SPIKE,
                "skipped": True,
                "reason": "P0_REJECT",
            },
        }
        evidence.append(tax_ev)
        return JudgmentDecision.REJECT, TI_TABLE_UNKNOWN, evidence

    w_ev = _warning_evidence(pw)
    if w_ev:
        evidence.append(w_ev)

    taxonomy, alternates, tax_features = _thin_taxonomy(table, cells, merges_list)
    tax_features["merge_count"] = len(merges_list)
    if alternates:
        tax_features["alternate_taxonomies"] = alternates

    tax_ev = {
        "rule_id": "J2-TAX-001",
        "conclusion": f"thin classifier primary taxonomy_code={taxonomy}",
        "targets": _bbox_targets(table),
        "refs_parse_warnings": [],
        "details": tax_features,
    }
    evidence.append(tax_ev)

    rc = _iter_cell_rc(cells)
    max_r = max((r for r, _ in rc), default=0)
    max_c = max((c for _, c in rc), default=0)
    r0, c0, r1, c1 = _effective_bbox_corners(table, max_r, max_c)
    evidence.extend(
        _row_col_primary_evidence(table, cells, r0, c0, r1, c1)
    )

    # スパイクでは人確認前提を維持（AUTO_ACCEPT は未使用）
    return JudgmentDecision.NEEDS_REVIEW, taxonomy, evidence
