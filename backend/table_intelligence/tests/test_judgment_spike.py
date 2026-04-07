"""
002 判定スパイク（P0 / warnings / 薄い J2-TAX）の単体・永続化テスト。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_judgment_spike.py
"""

from __future__ import annotations

import pytest

from table_intelligence.judgment_spike import (
    JUDGE_PROFILE_SPIKE,
    build_judgment_from_read_observation,
)
from table_intelligence.models import (
    AnalysisJob,
    JobStatus,
    JudgmentDecision,
    JudgmentResult,
    TableReadArtifact,
    TableScope,
    TI_TABLE_LIST_DETAIL,
    TI_TABLE_UNKNOWN,
)
from table_intelligence.services import ensure_mvp_judgment_result_for_table


def _scope(**kwargs) -> TableScope:
    return TableScope(**kwargs)


def test_p0_empty_cells_reject():
    table = _scope()
    d, tax, ev = build_judgment_from_read_observation(table, {}, [], [])
    assert d == JudgmentDecision.REJECT
    assert tax == TI_TABLE_UNKNOWN
    assert any(e.get("rule_id") == "J2-P0-001" for e in ev)
    assert all("judge_profile_id" in (e.get("details") or {}) for e in ev if e.get("details"))


def test_p0_cell_outside_bbox_reject():
    table = _scope(row_min=0, col_min=0, row_max=1, col_max=1)
    cells = {
        "R0C0": {"r": 0, "c": 0, "raw_display": "a"},
        "R9C9": {"r": 9, "c": 9, "raw_display": "x"},
    }
    d, tax, ev = build_judgment_from_read_observation(table, cells, [], [])
    assert d == JudgmentDecision.REJECT
    assert tax == TI_TABLE_UNKNOWN
    assert any(e.get("rule_id") == "J2-P0-003" for e in ev)


def test_p0_fatal_parse_warning_reject():
    table = _scope(row_min=0, col_min=0, row_max=1, col_max=1)
    cells = {"R0C0": {"r": 0, "c": 0, "raw_display": "1"}}
    pw = [{"code": "TI_READ_NO_TABLE_CANDIDATE", "severity": "warning", "message": "x"}]
    d, tax, ev = build_judgment_from_read_observation(table, cells, [], pw)
    assert d == JudgmentDecision.REJECT
    assert any(e.get("rule_id") == "J2-P0-004" for e in ev)
    p04 = next(e for e in ev if e.get("rule_id") == "J2-P0-004")
    assert p04["refs_parse_warnings"] == [0]


def test_parse_warnings_refs_when_nonfatal():
    table = _scope()
    cells = {"R0C0": {"r": 0, "c": 0, "raw_display": "a"}}
    pw = [
        {"code": "TI_READ_AMBIGUOUS", "severity": "info", "message": "a"},
        {"code": "TI_READ_SPARSE", "severity": "warning", "message": "b"},
    ]
    d, tax, ev = build_judgment_from_read_observation(table, cells, [], pw)
    assert d == JudgmentDecision.NEEDS_REVIEW
    warn = next(e for e in ev if e.get("rule_id") == "J2-WARN-001")
    assert warn["refs_parse_warnings"] == [0, 1]


def test_mvp_sparse_stub_unknown():
    """bbox なし・3 点対角で 3×3 スパン → 数値率が低く UNKNOWN に寄る。"""
    table = _scope()
    cells = {
        "R0C0": {"r": 0, "c": 0, "raw_display": ""},
        "R1C1": {"r": 1, "c": 1, "raw_display": ""},
        "R2C2": {"r": 2, "c": 2, "raw_display": ""},
    }
    d, tax, ev = build_judgment_from_read_observation(table, cells, [], [])
    assert d == JudgmentDecision.NEEDS_REVIEW
    assert tax == TI_TABLE_UNKNOWN
    tax_ev = next(e for e in ev if e.get("rule_id") == "J2-TAX-001")
    assert tax_ev["details"]["judge_profile_id"] == JUDGE_PROFILE_SPIKE
    assert "taxonomy_009" in tax_ev["details"]


def test_j2_row_col_primary_labels_in_evidence():
    """J2-ROW-001 / J2-COL-001 が 003 入力候補として details に載る。"""
    table = _scope(row_min=0, col_min=0, row_max=1, col_max=2)
    cells = {
        "R0C0": {"r": 0, "c": 0, "raw_display": "品目"},
        "R0C1": {"r": 0, "c": 1, "raw_display": "金額"},
        "R0C2": {"r": 0, "c": 2, "raw_display": "備考"},
        "R1C0": {"r": 1, "c": 0, "raw_display": "A"},
        "R1C1": {"r": 1, "c": 1, "raw_display": "100"},
        "R1C2": {"r": 1, "c": 2, "raw_display": ""},
    }
    d, _, ev = build_judgment_from_read_observation(table, cells, [], [])
    assert d == JudgmentDecision.NEEDS_REVIEW
    row_ev = next(e for e in ev if e.get("rule_id") == "J2-ROW-001")
    col_ev = next(e for e in ev if e.get("rule_id") == "J2-COL-001")
    assert row_ev["details"]["by_row_index"]["0"] == "ROW_HEADER_BAND"
    assert row_ev["details"]["intent"] == "normalization_input_hints_not_semantic_lock_in"
    assert col_ev["details"]["by_column_index"]["0"] == "COL_ATTRIBUTE_CANDIDATE"
    assert col_ev["details"]["by_column_index"]["1"] == "COL_MEASURE_CANDIDATE"


def test_crosstab_heuristic_promotes_when_009_axes_fail():
    """3×3 で数値率が高いが軸ラベルが取れない → クロス仮説はゲート不通過、一覧へ昇格しうる。"""
    table = _scope(row_min=0, col_min=0, row_max=2, col_max=2)
    cells = {
        f"R{i}C{i}": {"r": i, "c": i, "raw_display": str(100 + i)}
        for i in range(3)
    }
    d, tax, ev = build_judgment_from_read_observation(table, cells, [], [])
    assert d == JudgmentDecision.NEEDS_REVIEW
    assert tax == TI_TABLE_LIST_DETAIL
    tax_ev = next(e for e in ev if e.get("rule_id") == "J2-TAX-001")
    assert tax_ev["details"]["taxonomy_009"]["promoted_from_heuristic"]["to"] == TI_TABLE_LIST_DETAIL


@pytest.mark.django_db
def test_ensure_mvp_judgment_persist_reject_empty_cells(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=table,
        job=job,
        cells={},
        merges=[],
        parse_warnings=[],
        is_latest=True,
    )
    row = ensure_mvp_judgment_result_for_table(table=table, job=job)
    assert row.decision == JudgmentDecision.REJECT
    assert row.taxonomy_code == TI_TABLE_UNKNOWN
    assert any(e.get("rule_id") == "J2-P0-001" for e in row.evidence)


@pytest.mark.django_db
def test_ensure_mvp_judgment_refs_warnings(user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=table,
        job=job,
        cells={"R0C0": {"r": 0, "c": 0, "raw_display": "x"}},
        merges=[],
        parse_warnings=[
            {"code": "TI_READ_NOTE", "severity": "info", "message": "obs"},
        ],
        is_latest=True,
    )
    row = ensure_mvp_judgment_result_for_table(table=table, job=job)
    assert row.decision == JudgmentDecision.NEEDS_REVIEW
    assert JudgmentResult.objects.filter(table=table, is_latest=True).count() == 1
    warn = next(e for e in row.evidence if e.get("rule_id") == "J2-WARN-001")
    assert warn["refs_parse_warnings"] == [0]


@pytest.mark.django_db
def test_table_decision_api_shows_refs(auth_client, user):
    job = AnalysisJob.objects.create(
        workspace_id="ws-ti",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )
    table = TableScope.objects.create(job=job, workspace_id="ws-ti")
    TableReadArtifact.objects.create(
        workspace_id="ws-ti",
        table=table,
        job=job,
        cells={"R0C0": {"r": 0, "c": 0, "raw_display": "x"}},
        merges=[],
        parse_warnings=[{"code": "X", "severity": "warning", "message": "m"}],
        is_latest=True,
    )
    ensure_mvp_judgment_result_for_table(table=table, job=job)
    from django.urls import reverse

    url = reverse("ti-table-decision", kwargs={"table_id": table.table_id})
    res = auth_client.get(url)
    assert res.status_code == 200
    ev = res.data["evidence"]
    assert any("refs_parse_warnings" in e for e in ev)
    assert "decision_recommendation" not in res.data
