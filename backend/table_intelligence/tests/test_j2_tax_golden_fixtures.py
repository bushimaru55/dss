"""
J2-TAX-001 golden fixtures（009 軸ゲート較正の基準点）。

`judgment_spike` のロジックは変更せず、`build_judgment_from_read_observation` 経由で
taxonomy / taxonomy_009 の主要フィールドを固定する。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_j2_tax_golden_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from table_intelligence.judgment_spike import build_judgment_from_read_observation
from table_intelligence.models import JudgmentDecision, TableScope

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "j2_tax"

_GOLDEN_FILES = [
    "list_detail_texty_4x2.json",
    "time_series_3x6.json",
    "crosstab_4x4.json",
    "unknown_sparse_empty_diagonal.json",
    "key_value_2x3.json",
]


def _load_fixture(filename: str) -> dict:
    path = _FIXTURE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _table_from_scope(scope: dict) -> TableScope:
    kwargs = {}
    for k in ("row_min", "col_min", "row_max", "col_max"):
        if k in scope and scope[k] is not None:
            kwargs[k] = scope[k]
    return TableScope(**kwargs)


@pytest.mark.parametrize("filename", _GOLDEN_FILES)
def test_j2_tax_001_golden_via_build_judgment(filename):
    data = _load_fixture(filename)
    table = _table_from_scope(data.get("table_scope") or {})
    cells = data["cells"]
    merges = data.get("merges") or []
    exp = data["expected"]

    decision, taxonomy_code, evidence = build_judgment_from_read_observation(
        table, cells, merges, []
    )
    assert decision == JudgmentDecision.NEEDS_REVIEW
    assert taxonomy_code == exp["taxonomy_code"]

    tax_ev = next(e for e in evidence if e.get("rule_id") == "J2-TAX-001")
    t9 = tax_ev["details"]["taxonomy_009"]

    assert t9["heuristic_primary"] == exp["heuristic_primary"]
    assert t9["axis_gates_passed"] is exp["axis_gates_passed"]
    assert list(t9.get("axis_gate_failures") or []) == list(exp["axis_gate_failures"])

    if "promoted_from_heuristic" in exp:
        assert t9.get("promoted_from_heuristic") == exp["promoted_from_heuristic"]
