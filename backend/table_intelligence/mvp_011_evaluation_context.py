"""
011 MVP: ``ConfidenceEvaluation`` 応答に載せる **005 正本への読み取り参照**。

- ``confidence_score`` / ``risk_signals`` / ``decision_recommendation`` は 011 の出力のまま（上書きしない）。
- 同じ ``metadata`` に紐づく最新 ``HumanReviewSession`` があれば、その ``mvp_005_canonical_summary`` を **参照用**に添付する。
- 013 の提示制御・005 の状態更新は行わない。
"""

from __future__ import annotations

from typing import Any

from table_intelligence.mvp_005_review_state import build_mvp_005_canonical_review_summary
from table_intelligence.models import AnalysisMetadata, HumanReviewSession

MVP_011_REVIEW_STATE_REFERENCE_SCHEMA_REF = "ti.mvp_011_review_state_reference.v1"


def build_mvp_011_review_state_reference(metadata: AnalysisMetadata) -> dict[str, Any]:
    """
    GET ``/evaluations/<evaluation_ref>/`` 用の 005 参照ブロック。

    セッションが無い場合も 011 数値は別フィールドで返るため、ここは ``session_present: false`` とする。
    """
    session = (
        HumanReviewSession.objects.filter(metadata_id=metadata.metadata_id)
        .prefetch_related("suppression_records")
        .order_by("-created_at")
        .first()
    )
    if session is None:
        return {
            "schema_ref": MVP_011_REVIEW_STATE_REFERENCE_SCHEMA_REF,
            "semantic_lock_in": False,
            "session_present": False,
            "session_id": None,
            "mvp_005_canonical_summary": None,
            "note": (
                "no HumanReviewSession for this metadata; 011 confidence fields are unchanged"
            ),
        }
    return {
        "schema_ref": MVP_011_REVIEW_STATE_REFERENCE_SCHEMA_REF,
        "semantic_lock_in": False,
        "session_present": True,
        "session_id": str(session.session_id),
        "mvp_005_canonical_summary": build_mvp_005_canonical_review_summary(session),
        "note": (
            "read-only 005 canonical summary for context; does not merge into "
            "confidence_score or decision_recommendation"
        ),
    }
