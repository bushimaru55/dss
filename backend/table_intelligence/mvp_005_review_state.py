"""
005 MVP: HumanReviewSession 上の **正本の読み取り面**（保持済み状態の観測）。

- 004 の ``review_required`` / ``review_points`` はセッション作成時に snapshot 列へ取り込み済み（``create_review_session``）。
- 本モジュールは **新規に解決・確定しない**。downstream が参照する JSON サマリを組み立てるだけ。
- 011 の confidence / readiness、013 の提示制御は含めない。
"""

from __future__ import annotations

from typing import Any

from table_intelligence.models import HumanReviewSession, ReviewSessionState

MVP_005_CANONICAL_REVIEW_SUMMARY_SCHEMA_REF = "ti.mvp_005_canonical_review_summary.v1"


def suppression_record_count_for_session(session: HumanReviewSession) -> int:
    """``SuppressionRecord`` 件数。prefetch されていればキャッシュを使う。"""
    cache = getattr(session, "_prefetched_objects_cache", None)
    if cache and "suppression_records" in cache:
        return len(cache["suppression_records"])
    return session.suppression_records.count()


def build_mvp_005_canonical_review_summary(
    session: HumanReviewSession,
) -> dict[str, Any]:
    """
    005 正本状態の最小サマリ（自動解決・意味確定なし）。

    - ``resolution_status``: ``HumanReviewSession.state`` から導く粗い区分のみ。
    - ``suppression_status``: レコード有無のみ（レベルの解釈は別 API / 013 監査へ）。
    - ``unresolved_work_present``: ``RESOLVED`` 以外を未完了系として扱う（ビジネス確定ではない）。
    """
    rp_snap = session.review_points_snapshot
    n_points = len(rp_snap) if isinstance(rp_snap, list) else 0
    sup_n = suppression_record_count_for_session(session)

    state = session.state
    if state == ReviewSessionState.RESOLVED:
        resolution_status = "RESOLVED"
    elif state == ReviewSessionState.CLOSED_UNRESOLVED:
        resolution_status = "CLOSED_UNRESOLVED"
    else:
        resolution_status = "PENDING"

    suppression_status = "NONE" if sup_n == 0 else "PRESENT"

    uncertainty_intake_present = bool(session.review_required_snapshot) or n_points > 0
    unresolved_work_present = state != ReviewSessionState.RESOLVED

    return {
        "schema_ref": MVP_005_CANONICAL_REVIEW_SUMMARY_SCHEMA_REF,
        "semantic_lock_in": False,
        "review_state": state,
        "resolution_status": resolution_status,
        "resolution_grade": session.resolution_grade,
        "suppression_status": suppression_status,
        "suppression_record_count": sup_n,
        "unresolved_work_present": unresolved_work_present,
        "uncertainty_intake_present": uncertainty_intake_present,
        "from_004_review_required_snapshot": session.review_required_snapshot,
        "from_004_review_point_count_at_intake": n_points,
        "note": (
            "005 canonical read surface; 004 review_required/review_points captured at "
            "session create; not 011 confidence/readiness/caution nor 013 suggestion control"
        ),
    }
