"""
013 MVP: 候補生成まわりの **005 / 011 読み取り参照面**（提示制御ロジックは持たない）。

- ``primary_constraints_from_005``: ``build_mvp_005_canonical_review_summary`` の結果（再定義しない）。
- ``auxiliary_signals_from_011``: 最新 ``ConfidenceEvaluation`` の数値・推奨・risk（再計算しない）。
- 未解決を確定候補に昇格させない。suppression の正本は 005 のまま（SuggestionSet へ移さない）。
"""

from __future__ import annotations

from typing import Any

from table_intelligence.mvp_005_review_state import build_mvp_005_canonical_review_summary
from table_intelligence.models import (
    ConfidenceEvaluation,
    HumanReviewSession,
    SuggestionSet,
)

MVP_013_GENERATION_CONSTRAINTS_REFERENCE_SCHEMA_REF = (
    "ti.mvp_013_generation_constraints_reference.v1"
)


def build_mvp_013_generation_constraints_reference(sset: SuggestionSet) -> dict[str, Any]:
    """
    ``GET /suggestion-runs/<id>/`` 用。同一 ``metadata`` の最新 005 セッション・最新 011 評価を参照するだけ。
    """
    meta = sset.metadata
    session = (
        HumanReviewSession.objects.filter(metadata_id=meta.metadata_id)
        .prefetch_related("suppression_records")
        .order_by("-created_at")
        .first()
    )
    primary: dict[str, Any] | None = None
    if session is not None:
        primary = build_mvp_005_canonical_review_summary(session)

    ev = (
        ConfidenceEvaluation.objects.filter(metadata_id=meta.metadata_id)
        .order_by("-created_at")
        .first()
    )
    auxiliary: dict[str, Any] | None = None
    if ev is not None:
        auxiliary = {
            "evaluation_ref": str(ev.evaluation_id),
            "confidence_score": ev.confidence_score,
            "decision_recommendation": ev.decision_recommendation,
            "risk_signals": list(ev.risk_signals)
            if isinstance(ev.risk_signals, list)
            else [],
        }

    return {
        "schema_ref": MVP_013_GENERATION_CONSTRAINTS_REFERENCE_SCHEMA_REF,
        "semantic_lock_in": False,
        "primary_constraints_from_005": primary,
        "auxiliary_signals_from_011": auxiliary,
        "note": (
            "013 observation only: 005 fields are primary constraints; 011 is auxiliary; "
            "does not promote unresolved work to confirmed candidates or override suppression"
        ),
    }
