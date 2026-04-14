"""
``summarize_review_outcome_for_candidates`` の局所テスト（013 内部契約）。

    DJANGO_SETTINGS_MODULE=config.settings.test pytest table_intelligence/tests/test_mvp_013_candidate_review_signal.py
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    HumanReviewSession,
    JobStatus,
    NormalizedDataset,
    ReviewSessionState,
    SuppressionLevel,
    SuppressionRecord,
    TableScope,
)
from table_intelligence.mvp_013_candidate_review_signal import (
    REVIEW_GAP_STUB_RISK_NOTE_BLOCKING,
    REVIEW_GAP_STUB_RISK_NOTE_CAUTION,
    CandidateReviewSignal,
    review_gap_risk_note_for_candidates,
    summarize_review_outcome_for_candidates,
)
from table_intelligence.services import (
    _append_unique_risk_note,
    _should_skip_stub_candidate_for_blocking_review_gap,
)


@pytest.fixture
def ti_job(user):
    return AnalysisJob.objects.create(
        workspace_id="ws-ti-rs",
        status=JobStatus.SUCCEEDED,
        requested_by=user,
    )


@pytest.fixture
def ti_table(ti_job):
    return TableScope.objects.create(job=ti_job, workspace_id="ws-ti-rs")


@pytest.fixture
def ti_dataset(ti_job, ti_table):
    return NormalizedDataset.objects.create(
        workspace_id="ws-ti-rs",
        job=ti_job,
        table=ti_table,
        schema_version="0.1",
        dataset_payload={"rows": []},
    )


@pytest.fixture
def ti_metadata(ti_dataset):
    return AnalysisMetadata.objects.create(
        dataset=ti_dataset,
        workspace_id="ws-ti-rs",
        review_required=True,
        review_points=[],
        dimensions=[],
        measures=[{"id": "m1"}],
        decision={},
    )


@pytest.mark.django_db
def test_summarize_no_session():
    sig = summarize_review_outcome_for_candidates(None)
    assert sig == {
        "review_signal_present": False,
        "has_blocking_review_gap": False,
        "has_cautionary_review_gap": False,
        "has_resolution_support": False,
    }


@pytest.mark.django_db
def test_summarize_resolved_support_only(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.RESOLVED,
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    SuppressionRecord.objects.create(
        session=s,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_BLOCKED,
        suppression_reason="should not leak into signal when resolved",
        suppressed_targets=[],
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["review_signal_present"] is True
    assert sig["has_resolution_support"] is True
    assert sig["has_blocking_review_gap"] is False
    assert sig["has_cautionary_review_gap"] is False


@pytest.mark.django_db
def test_summarize_open_blocking(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["review_signal_present"] is True
    assert sig["has_blocking_review_gap"] is True
    assert sig["has_cautionary_review_gap"] is False
    assert sig["has_resolution_support"] is False


@pytest.mark.django_db
def test_summarize_in_progress_caution(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.IN_PROGRESS,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["has_cautionary_review_gap"] is True
    assert sig["has_blocking_review_gap"] is False
    assert sig["has_resolution_support"] is False


@pytest.mark.django_db
def test_summarize_closed_unresolved_blocking(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.CLOSED_UNRESOLVED,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["has_blocking_review_gap"] is True
    assert sig["has_cautionary_review_gap"] is False


@pytest.mark.django_db
def test_summarize_suppression_blocked_overlays(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.IN_PROGRESS,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    SuppressionRecord.objects.create(
        session=s,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_BLOCKED,
        suppression_reason="block",
        suppressed_targets=[],
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["has_blocking_review_gap"] is True
    assert sig["has_cautionary_review_gap"] is True


@pytest.mark.django_db
def test_summarize_suppression_limited_adds_caution(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state=ReviewSessionState.OPEN,
        review_required_snapshot=True,
        review_points_snapshot=[],
        created_by=user,
    )
    SuppressionRecord.objects.create(
        session=s,
        workspace_id="ws-ti",
        suppression_level=SuppressionLevel.SUGGESTION_LIMITED,
        suppression_reason="lim",
        suppressed_targets=[],
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["has_blocking_review_gap"] is True
    assert sig["has_cautionary_review_gap"] is True


@pytest.mark.django_db
def test_summarize_unknown_state_conservative(ti_metadata, user):
    s = HumanReviewSession.objects.create(
        metadata=ti_metadata,
        workspace_id="ws-ti",
        state="WEIRD_UNSET",  # type: ignore[arg-type]
        review_required_snapshot=False,
        review_points_snapshot=[],
        created_by=user,
    )
    sig = summarize_review_outcome_for_candidates(s)
    assert sig["review_signal_present"] is True
    assert sig["has_blocking_review_gap"] is True
    assert sig["has_cautionary_review_gap"] is False


def test_review_gap_risk_note_absent_when_no_signal():
    sig: CandidateReviewSignal = {
        "review_signal_present": False,
        "has_blocking_review_gap": False,
        "has_cautionary_review_gap": False,
        "has_resolution_support": False,
    }
    assert review_gap_risk_note_for_candidates(sig) is None


def test_review_gap_risk_note_blocking():
    sig: CandidateReviewSignal = {
        "review_signal_present": True,
        "has_blocking_review_gap": True,
        "has_cautionary_review_gap": True,
        "has_resolution_support": False,
    }
    assert review_gap_risk_note_for_candidates(sig) == REVIEW_GAP_STUB_RISK_NOTE_BLOCKING


def test_review_gap_risk_note_caution_only_when_no_blocking():
    sig: CandidateReviewSignal = {
        "review_signal_present": True,
        "has_blocking_review_gap": False,
        "has_cautionary_review_gap": True,
        "has_resolution_support": False,
    }
    assert review_gap_risk_note_for_candidates(sig) == REVIEW_GAP_STUB_RISK_NOTE_CAUTION


def test_review_gap_risk_note_resolution_only_no_append():
    sig: CandidateReviewSignal = {
        "review_signal_present": True,
        "has_blocking_review_gap": False,
        "has_cautionary_review_gap": False,
        "has_resolution_support": True,
    }
    assert review_gap_risk_note_for_candidates(sig) is None


def test_append_unique_risk_note_skips_empty():
    base = ["a"]
    assert _append_unique_risk_note(base, None) is base
    assert _append_unique_risk_note(base, "") is base


def test_append_unique_risk_note_appends_once():
    base = ["x"]
    out = _append_unique_risk_note(base, "y")
    assert out == ["x", "y"]
    assert out is not base


def test_append_unique_risk_note_no_duplicate():
    base = ["a", REVIEW_GAP_STUB_RISK_NOTE_BLOCKING]
    assert _append_unique_risk_note(base, REVIEW_GAP_STUB_RISK_NOTE_BLOCKING) is base


def _sig(
    *,
    present: bool = True,
    blocking: bool = False,
    caution: bool = False,
    support: bool = False,
) -> CandidateReviewSignal:
    return {
        "review_signal_present": present,
        "has_blocking_review_gap": blocking,
        "has_cautionary_review_gap": caution,
        "has_resolution_support": support,
    }


def test_should_skip_blocking_absent_never_skips():
    meta = SimpleNamespace(time_axis={"grain": "month"})
    assert (
        _should_skip_stub_candidate_for_blocking_review_gap(
            stub_category="summary_stub",
            metadata=meta,  # type: ignore[arg-type]
            review_signal=_sig(blocking=False),
        )
        is False
    )


def test_should_skip_blocking_with_time_axis_skips():
    meta = SimpleNamespace(time_axis={"grain": "month"})
    assert (
        _should_skip_stub_candidate_for_blocking_review_gap(
            stub_category="summary_stub",
            metadata=meta,  # type: ignore[arg-type]
            review_signal=_sig(blocking=True),
        )
        is True
    )


def test_should_skip_blocking_without_time_axis_does_not_skip():
    meta = SimpleNamespace(time_axis=None)
    assert (
        _should_skip_stub_candidate_for_blocking_review_gap(
            stub_category="summary_stub",
            metadata=meta,  # type: ignore[arg-type]
            review_signal=_sig(blocking=True),
        )
        is False
    )


def test_should_skip_wrong_category_never_skips():
    meta = SimpleNamespace(time_axis={"grain": "month"})
    assert (
        _should_skip_stub_candidate_for_blocking_review_gap(
            stub_category="other_stub",
            metadata=meta,  # type: ignore[arg-type]
            review_signal=_sig(blocking=True),
        )
        is False
    )


def test_should_skip_caution_only_with_time_axis_does_not_skip():
    meta = SimpleNamespace(time_axis={"grain": "month"})
    assert (
        _should_skip_stub_candidate_for_blocking_review_gap(
            stub_category="summary_stub",
            metadata=meta,  # type: ignore[arg-type]
            review_signal=_sig(blocking=False, caution=True),
        )
        is False
    )


def test_should_skip_resolution_only_with_time_axis_does_not_skip():
    meta = SimpleNamespace(time_axis={"grain": "month"})
    assert (
        _should_skip_stub_candidate_for_blocking_review_gap(
            stub_category="summary_stub",
            metadata=meta,  # type: ignore[arg-type]
            review_signal=_sig(blocking=False, caution=False, support=True),
        )
        is False
    )
