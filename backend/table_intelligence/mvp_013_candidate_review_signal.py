"""
013 MVP: 005 由来のレビュー outcome を **候補判断向けにだけ** 要約する内部アダプタ。

- HumanReviewSession / SuppressionRecord を **読むだけ**（遷移・再解決・正本の複写はしない）。
- 戻り値は 013 内部の boolean 意味面のみ（public API 契約ではない）。
- 005 の state machine や resolution grade を 013 側で再制度しない。
"""

from __future__ import annotations

from typing import TypedDict

from table_intelligence.models import (
    HumanReviewSession,
    ReviewSessionState,
    SuppressionLevel,
)


class CandidateReviewSignal(TypedDict):
    """013 候補生成 / suppression / caution 分岐が参照する最小意味面（内部専用）。"""

    review_signal_present: bool
    has_blocking_review_gap: bool
    has_cautionary_review_gap: bool
    has_resolution_support: bool


# スタブ候補 ``risk_notes`` 用の短文（説明補足であり制度・契約ではない）
REVIEW_GAP_STUB_RISK_NOTE_BLOCKING = (
    "人確認に未解決の点があるため、この候補は追加確認前提です。"
)
REVIEW_GAP_STUB_RISK_NOTE_CAUTION = (
    "人確認が進行中のため、この候補は注意付きで参照してください。"
)


def review_gap_risk_note_for_candidates(review_signal: CandidateReviewSignal) -> str | None:
    """
    ``review_signal`` をスタブ候補の ``risk_notes`` 追記用に 1 文へ落とす。

    blocking を caution より優先する。``has_resolution_support`` は追記に使わない（Phase 3 第二段）。
    """
    if not review_signal["review_signal_present"]:
        return None
    if review_signal["has_blocking_review_gap"]:
        return REVIEW_GAP_STUB_RISK_NOTE_BLOCKING
    if review_signal["has_cautionary_review_gap"]:
        return REVIEW_GAP_STUB_RISK_NOTE_CAUTION
    return None


def summarize_review_outcome_for_candidates(
    session: HumanReviewSession | None,
) -> CandidateReviewSignal:
    """
    最新の 005 セッション観測から、013 スタブ/将来の候補ロジック用の信号へ要約する。

    suppression_records は prefetch されていればキャッシュを使う（``.all()``）。
    """
    empty: CandidateReviewSignal = {
        "review_signal_present": False,
        "has_blocking_review_gap": False,
        "has_cautionary_review_gap": False,
        "has_resolution_support": False,
    }
    if session is None:
        return empty

    state = session.state
    if state == ReviewSessionState.RESOLVED:
        return {
            "review_signal_present": True,
            "has_blocking_review_gap": False,
            "has_cautionary_review_gap": False,
            "has_resolution_support": True,
        }

    blocking = False
    caution = False
    if state == ReviewSessionState.IN_PROGRESS:
        caution = True
    elif state in (ReviewSessionState.OPEN, ReviewSessionState.CLOSED_UNRESOLVED):
        blocking = True
    else:
        # 想定外の保持値でも落とさず、候補側は強く主張しにくい側へ寄せる
        blocking = True

    for rec in session.suppression_records.all():
        lvl = rec.suppression_level
        if lvl == SuppressionLevel.SUGGESTION_BLOCKED:
            blocking = True
        elif lvl in (
            SuppressionLevel.SUGGESTION_LIMITED,
            SuppressionLevel.SUGGESTION_ALLOWED_WITH_CAUTION,
        ):
            caution = True

    return {
        "review_signal_present": True,
        "has_blocking_review_gap": blocking,
        "has_cautionary_review_gap": caution,
        "has_resolution_support": False,
    }
