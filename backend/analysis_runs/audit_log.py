"""
ブラウザから実行した分析を、ワークスペース上の JSONL で追跡する。

Cursor 等で backend/logs/analysis_audit.jsonl を開くと、ファクトと回答の突合に使える。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from analysis_runs.models import AnalysisRun

_NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _facts_summary(facts: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in (
        "schema_version",
        "row_count",
        "query_intent",
        "amount_sum",
        "amount_avg",
    ):
        if k in facts:
            out[k] = facts[k]
    for k in ("top_customers", "top_by_person"):
        v = facts.get(k)
        if isinstance(v, list):
            out[k] = v[:3]
    v = facts.get("status_distribution")
    if isinstance(v, list):
        out["status_distribution"] = v[:5]
    return out


def _numbers_in_text(text: str) -> set[float]:
    nums: set[float] = set()
    for m in _NUM_RE.finditer(text.replace(",", "")):
        s = m.group(0)
        if s in "-." or s == "":
            continue
        try:
            nums.add(float(s))
        except ValueError:
            continue
    return nums


def _numbers_from_facts(facts: dict[str, Any]) -> set[float]:
    nums: set[float] = set()
    for key in ("amount_sum", "amount_avg", "row_count"):
        v = facts.get(key)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            nums.add(float(v))
    for key in ("top_customers", "top_by_person"):
        for row in facts.get(key) or []:
            if isinstance(row, dict) and isinstance(row.get("amount"), (int, float)):
                nums.add(float(row["amount"]))
    for row in facts.get("status_distribution") or []:
        if isinstance(row, dict) and isinstance(row.get("count"), (int, float)):
            nums.add(float(row["count"]))
    return nums


def build_auto_checks(answer: str, facts: dict[str, Any]) -> dict[str, Any]:
    """回答に含まれる数値がファクト由来と見なせるかの簡易ヒューリスティック。"""
    an = _numbers_in_text(answer or "")
    fn = _numbers_from_facts(facts)
    only_answer = sorted(an - fn)
    # 年号っぽい整数はノイズになりやすいのでフラグから除外
    only_answer_f = [x for x in only_answer if not (1900 <= x <= 2100 and x == int(x))]
    suspected = bool(only_answer_f) and bool(fn)
    return {
        "numbers_in_answer_sample": sorted(an)[:24],
        "numbers_in_facts_sample": sorted(fn)[:24],
        "numbers_only_in_answer": only_answer_f[:12],
        "suspected_ungrounded_numbers": suspected,
    }


def _audit_log_path() -> Path:
    p = getattr(settings, "ANALYSIS_AUDIT_LOG_PATH", None)
    if p is None:
        return Path(settings.BASE_DIR) / "logs" / "analysis_audit.jsonl"
    return Path(p)


def append_audit_record_for_run(run: AnalysisRun) -> None:
    """1 実行につき 1 行 JSONL を追記する。"""
    path = _audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = build_audit_record(run)
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def build_audit_record(run: AnalysisRun) -> dict[str, Any]:
    facts = run.result_json if isinstance(run.result_json, dict) else {}
    evidence = run.evidence if isinstance(run.evidence, dict) else {}
    rec: dict[str, Any] = {
        "ts": timezone.now().isoformat(),
        "run_id": run.id,
        "dataset_id": run.dataset_id,
        "status": run.status,
        "question": (run.question or "")[:4000],
        "review_hint": "Cursor: workspace の backend/logs/analysis_audit.jsonl を開いて精度レビュー",
    }
    if run.status == AnalysisRun.Status.SUCCEEDED:
        rec["facts_summary"] = _facts_summary(facts)
        rec["answer_excerpt"] = (run.answer or "")[:1200]
        rec["confidence"] = float(run.confidence or 0.0)
        rag = evidence.get("rag_items") or []
        rec["rag_titles"] = [str(r.get("title", "")) for r in rag[:8] if isinstance(r, dict)]
        rec["fact_keys"] = list(evidence.get("fact_keys") or [])[:64]
        rec["auto_checks"] = build_auto_checks(run.answer or "", facts)
    else:
        rec["error_message"] = (run.error_message or "")[:2000]
    return rec


def read_recent_audit_entries(*, max_lines: int = 200) -> list[dict[str, Any]]:
    """直近 max_lines 行をパース（新しい順）。"""
    path = _audit_log_path()
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()[-max_lines:]
    out: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    out.reverse()
    return out
