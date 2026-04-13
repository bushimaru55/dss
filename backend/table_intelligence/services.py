"""
表解析ジョブのユースケース層（MVP）。

非同期投入は ``table_intelligence.pipeline.schedule_mvp_pipeline``（django-rq）経由。
rerun 由来の lineage は ``request_payload["lineage"]`` と ``artifact_relation`` に記録する。
"""

from __future__ import annotations

import uuid

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from table_intelligence.judgment_spike import build_judgment_from_read_observation
from table_intelligence.mvp_004_dataset_inputs import apply_mvp_004_dataset_input_reflection
from table_intelligence.normalization_hints import (
    assemble_mvp_003_dataset_payload_artifacts,
    extract_normalization_input_hints_from_judgment_evidence,
    merge_hints_into_dataset_payload,
    read_normalization_input_hints_from_dataset_payload,
)
from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ArtifactRelation,
    ConfidenceEvaluation,
    HumanReviewAnswer,
    HumanReviewSession,
    JobStatus,
    JudgmentDecision,
    JudgmentResult,
    NormalizedDataset,
    TableReadArtifact,
    ReviewSessionState,
    SuggestionSet,
    TableScope,
)

LINEAGE_RELATION_JOB_RERUN = "TI_JOB_RERUN_SUPERSEDES"
LINEAGE_RELATION_REVIEW_RERUN = "TI_REVIEW_RERUN_SUPERSEDES"


class StaleMetadataError(Exception):
    """
    ``analysis_metadata`` が ``artifact_relation`` 上で既に superseded されている。
    API は 409 ``TI_CONFLICT`` にマッピングする（014 §13.1）。
    """


def metadata_is_superseded(metadata: AnalysisMetadata) -> bool:
    """
    同一 workspace 内で、当該 metadata が **旧側**（from）の
    ``TI_*_SUPERSEDES`` edge を持つなら True。

    ``record_lineage_relations_after_materialize`` が書く
    ``analysis_metadata -> analysis_metadata`` の relation に依存する。
    """
    mid = str(metadata.metadata_id)
    ws = metadata.workspace_id
    return ArtifactRelation.objects.filter(
        workspace_id=ws,
        relation_type__in=(LINEAGE_RELATION_JOB_RERUN, LINEAGE_RELATION_REVIEW_RERUN),
        from_artifact_type=ARTIFACT_TYPE_METADATA,
        from_artifact_id=mid,
        to_artifact_type=ARTIFACT_TYPE_METADATA,
    ).exists()

ARTIFACT_TYPE_JOB = "analysis_job"
ARTIFACT_TYPE_DATASET = "normalized_dataset"
ARTIFACT_TYPE_METADATA = "analysis_metadata"
ARTIFACT_TYPE_SESSION = "human_review_session"
ARTIFACT_TYPE_SUGGESTION = "suggestion_set"
ARTIFACT_TYPE_JUDGMENT = "judgment_result"
ARTIFACT_TYPE_READ_ARTIFACT = "table_read_artifact"


def collect_artifact_refs_bundle_for_dataset(dataset: NormalizedDataset) -> dict[str, str]:
    """
    014 ``ArtifactRefs`` 互換の参照束。

    metadata 未生成時も ``dataset_id`` / ``table_id`` を返す（table 起点の一覧用）。
    job 経路の冪等復元では metadata 無しの場合は空 dict を返す別ロジックを維持する。
    """
    table_id = str(dataset.table_id) if dataset.table_id else ""
    meta = AnalysisMetadata.objects.filter(dataset=dataset).first()
    if meta is None:
        return {
            "table_id": table_id,
            "dataset_id": str(dataset.dataset_id),
            "metadata_id": "",
            "evaluation_ref": "",
            "session_id": "",
            "suggestion_run_ref": "",
        }
    ev = (
        ConfidenceEvaluation.objects.filter(metadata_id=meta.metadata_id)
        .order_by("-created_at")
        .first()
    )
    session = (
        HumanReviewSession.objects.filter(metadata_id=meta.metadata_id)
        .order_by("-created_at")
        .first()
    )
    suggestion = (
        SuggestionSet.objects.filter(metadata_id=meta.metadata_id)
        .order_by("-created_at")
        .first()
    )
    return {
        "table_id": table_id,
        "dataset_id": str(dataset.dataset_id),
        "metadata_id": str(meta.metadata_id),
        "evaluation_ref": str(ev.evaluation_id) if ev else "",
        "session_id": str(session.session_id) if session else "",
        "suggestion_run_ref": str(suggestion.suggestion_run_id) if suggestion else "",
    }


def _collect_artifact_refs_from_job(job: AnalysisJob) -> dict[str, str]:
    """既に紐づく MVP 成果物から参照 ID を復元する（冪等用）。"""
    dataset = (
        NormalizedDataset.objects.filter(job=job)
        .select_related("table")
        .first()
    )
    if dataset is None:
        return {}
    if not AnalysisMetadata.objects.filter(dataset=dataset).exists():
        return {}
    return collect_artifact_refs_bundle_for_dataset(dataset)


def get_artifact_ref_bundles_for_table(table: TableScope) -> list[dict[str, str]]:
    """同一 ``TableScope`` にぶら下がる ``NormalizedDataset`` ごとに参照束を列挙（新しい順）。"""
    qs = (
        NormalizedDataset.objects.filter(table=table)
        .select_related("table")
        .order_by("-created_at")
    )
    return [collect_artifact_refs_bundle_for_dataset(ds) for ds in qs]


def get_latest_artifact_refs_for_table(table: TableScope) -> dict[str, str]:
    """``TableSummary.refs`` 用: 最新データセット列の参照束。データセットが無い場合は ``table_id`` のみ。"""
    bundles = get_artifact_ref_bundles_for_table(table)
    if bundles:
        return bundles[0]
    return {
        "table_id": str(table.table_id),
        "dataset_id": "",
        "metadata_id": "",
        "evaluation_ref": "",
        "session_id": "",
        "suggestion_run_ref": "",
    }


def get_latest_judgment_result_for_table(table: TableScope) -> JudgmentResult | None:
    """
    002 永続行の latest 解決（015 ``is_latest``）。

    ``uniq_judgment_result_latest_per_table`` により ``is_latest=True`` は table あたり高々1件。
    """
    return JudgmentResult.objects.filter(table=table, is_latest=True).first()


def _apply_judgment_hints_to_normalized_dataset(
    *, dataset: NormalizedDataset, table: TableScope
) -> None:
    """
    最新 ``JudgmentResult.evidence`` の J2-ROW / J2-COL を
    ``dataset_payload.normalization_input_hints`` に載せ、003 MVP が
    ``rows[]`` / ``trace_map`` / ``column_slots[]`` をヒントに基づき組み立てる（最小接続）。
    """
    row = get_latest_judgment_result_for_table(table)
    if row is None:
        return
    hints = extract_normalization_input_hints_from_judgment_evidence(row.evidence)
    if hints is None:
        return
    base = dataset.dataset_payload if isinstance(dataset.dataset_payload, dict) else {}
    merged = merge_hints_into_dataset_payload(base, hints)
    hints_for_stub = read_normalization_input_hints_from_dataset_payload(merged) or hints
    read_art = get_latest_table_read_artifact_for_table(table)
    cell_map = (
        dict(read_art.cells)
        if read_art is not None and isinstance(read_art.cells, dict)
        else {}
    )
    stub_rows, stub_trace, stub_meta, stub_column_slots = (
        assemble_mvp_003_dataset_payload_artifacts(
            hints_for_stub, table=table, cells=cell_map
        )
    )
    merged["rows"] = stub_rows
    merged["trace_map"] = stub_trace
    merged["column_slots"] = stub_column_slots
    merged["mvp_normalization_stub"] = stub_meta
    dataset.dataset_payload = merged
    dataset.save(update_fields=["dataset_payload", "updated_at"])


def judgment_result_to_judgment_api_dict(row: JudgmentResult) -> dict[str, object]:
    """OpenAPI / 006 ``JudgmentResult`` 形（``GET /tables/{table_id}/decision`` 差し替え用）。"""
    return {
        "judgment_id": str(row.judgment_id),
        "table_id": str(row.table_id),
        "decision": row.decision,
        "taxonomy_code": row.taxonomy_code,
        "evidence": list(row.evidence) if row.evidence is not None else [],
    }


def get_latest_table_read_artifact_for_table(table: TableScope) -> TableReadArtifact | None:
    """
    001/006 ``TableReadArtifact`` の latest 行（015 ``is_latest``）。

    ``uniq_table_read_artifact_latest_per_table`` により ``is_latest=True`` は table あたり高々1件。
    """
    return TableReadArtifact.objects.filter(table=table, is_latest=True).first()


def table_read_artifact_to_api_dict(row: TableReadArtifact) -> dict[str, object]:
    """OpenAPI / 006 ``TableReadArtifact`` 形（``GET /tables/{table_id}/read-artifact`` 差し替え用）。"""
    return {
        "artifact_id": str(row.artifact_id),
        "table_id": str(row.table_id),
        "cells": dict(row.cells) if row.cells is not None else {},
        "merges": list(row.merges) if row.merges is not None else [],
        "parse_warnings": list(row.parse_warnings) if row.parse_warnings is not None else [],
    }


def get_artifact_refs_for_job(job: AnalysisJob) -> dict[str, str] | None:
    """014 ジョブ詳細に載せうる参照束。未生成時は ``None``。"""
    refs = _collect_artifact_refs_from_job(job)
    return refs if refs.get("dataset_id") else None


def _finalize_job_success(job: AnalysisJob, refs: dict[str, str]) -> None:
    payload = dict(job.request_payload or {})
    payload["mvp_pipeline"] = {"version": 1, **refs}
    now = timezone.now()
    job.request_payload = payload
    job.status = JobStatus.SUCCEEDED
    job.current_stage = "mvp_pipeline_materialized"
    job.completed_at = now
    job.save(
        update_fields=[
            "request_payload",
            "status",
            "current_stage",
            "completed_at",
            "updated_at",
        ]
    )


def _try_create_artifact_relation(
    *,
    workspace_id: str,
    relation_type: str,
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    context_job_id: uuid.UUID,
) -> None:
    if not from_id or not to_id:
        return
    ArtifactRelation.objects.get_or_create(
        workspace_id=workspace_id,
        relation_type=relation_type,
        from_artifact_type=from_type,
        from_artifact_id=from_id,
        to_artifact_type=to_type,
        to_artifact_id=to_id,
        context_job_id=context_job_id,
        defaults={},
    )


def record_lineage_relations_after_materialize(
    *,
    job: AnalysisJob,
    refs: dict[str, str],
) -> None:
    """
    ``request_payload["lineage"]`` が rerun 由来のとき、旧→新の SUPERSEDES 相当 edge を記録する。

    ``prior_workspace_id`` が ``job.workspace_id`` と一致しない場合は何もしない（越境防止）。
    """
    payload = job.request_payload or {}
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        return
    relation_type = lineage.get("relation_type")
    if relation_type not in (
        LINEAGE_RELATION_JOB_RERUN,
        LINEAGE_RELATION_REVIEW_RERUN,
    ):
        return
    prior_ws = lineage.get("prior_workspace_id")
    if prior_ws != job.workspace_id:
        return
    ws = job.workspace_id
    cid = job.job_id
    pairs: list[tuple[str, str, str, str]] = [
        (ARTIFACT_TYPE_METADATA, "prior_metadata_id", ARTIFACT_TYPE_METADATA, "metadata_id"),
        (ARTIFACT_TYPE_DATASET, "prior_dataset_id", ARTIFACT_TYPE_DATASET, "dataset_id"),
        (ARTIFACT_TYPE_SESSION, "prior_session_id", ARTIFACT_TYPE_SESSION, "session_id"),
        (
            ARTIFACT_TYPE_SUGGESTION,
            "prior_suggestion_run_id",
            ARTIFACT_TYPE_SUGGESTION,
            "suggestion_run_ref",
        ),
    ]
    for from_t, lk_old, to_t, lk_new in pairs:
        old = lineage.get(lk_old)
        new = refs.get(lk_new)
        if old and new:
            _try_create_artifact_relation(
                workspace_id=ws,
                relation_type=relation_type,
                from_type=from_t,
                from_id=str(old),
                to_type=to_t,
                to_id=str(new),
                context_job_id=cid,
            )
    if relation_type == LINEAGE_RELATION_JOB_RERUN:
        src_job = lineage.get("source_job_id")
        if src_job:
            _try_create_artifact_relation(
                workspace_id=ws,
                relation_type=relation_type,
                from_type=ARTIFACT_TYPE_JOB,
                from_id=str(src_job),
                to_type=ARTIFACT_TYPE_JOB,
                to_id=str(job.job_id),
                context_job_id=cid,
            )

    _apply_judgment_supersedes_on_lineage(
        job=job,
        refs=refs,
        lineage=lineage,
        relation_type=relation_type,
        workspace_id=ws,
        context_job_id=cid,
    )
    _apply_read_artifact_supersedes_on_lineage(
        job=job,
        refs=refs,
        lineage=lineage,
        relation_type=relation_type,
        workspace_id=ws,
        context_job_id=cid,
    )


def _apply_read_artifact_supersedes_on_lineage(
    *,
    job: AnalysisJob,
    refs: dict[str, str],
    lineage: dict,
    relation_type: str,
    workspace_id: str,
    context_job_id: uuid.UUID,
) -> None:
    """
    rerun / review-rerun 時: 旧 ``table_id`` 上の ``TableReadArtifact.is_latest`` を落とし、
    旧→新 ``artifact_id`` を ``artifact_relation`` に載せる（015 / 001 器）。

    001 の観測 JSON は行を UPDATE せず、世代は **新行 + 旧 latest フラグ解除**で表す。
    """
    if relation_type not in (
        LINEAGE_RELATION_JOB_RERUN,
        LINEAGE_RELATION_REVIEW_RERUN,
    ):
        return
    prior_table_id = lineage.get("prior_table_id")
    new_table_id = refs.get("table_id")
    if not prior_table_id or not new_table_id:
        return
    if str(prior_table_id) == str(new_table_id):
        return
    new_ra = TableReadArtifact.objects.filter(job=job, table_id=new_table_id).first()
    prior_aid = lineage.get("prior_read_artifact_id")
    if prior_aid and new_ra:
        _try_create_artifact_relation(
            workspace_id=workspace_id,
            relation_type=relation_type,
            from_type=ARTIFACT_TYPE_READ_ARTIFACT,
            from_id=str(prior_aid),
            to_type=ARTIFACT_TYPE_READ_ARTIFACT,
            to_id=str(new_ra.artifact_id),
            context_job_id=context_job_id,
        )
    TableReadArtifact.objects.filter(
        table_id=prior_table_id, is_latest=True
    ).update(is_latest=False)


def _apply_judgment_supersedes_on_lineage(
    *,
    job: AnalysisJob,
    refs: dict[str, str],
    lineage: dict,
    relation_type: str,
    workspace_id: str,
    context_job_id: uuid.UUID,
) -> None:
    """
    rerun / review-rerun 時: 旧 ``table_id`` 上の ``JudgmentResult.is_latest`` を落とし、
    旧→新 ``judgment_id`` を ``artifact_relation`` に載せる（015 lineage / 002 器）。

    011 は関与しない。
    """
    if relation_type not in (
        LINEAGE_RELATION_JOB_RERUN,
        LINEAGE_RELATION_REVIEW_RERUN,
    ):
        return
    prior_table_id = lineage.get("prior_table_id")
    new_table_id = refs.get("table_id")
    if not prior_table_id or not new_table_id:
        return
    if str(prior_table_id) == str(new_table_id):
        return
    new_j = JudgmentResult.objects.filter(job=job, table_id=new_table_id).first()
    prior_jid = lineage.get("prior_judgment_id")
    if prior_jid and new_j:
        _try_create_artifact_relation(
            workspace_id=workspace_id,
            relation_type=relation_type,
            from_type=ARTIFACT_TYPE_JUDGMENT,
            from_id=str(prior_jid),
            to_type=ARTIFACT_TYPE_JUDGMENT,
            to_id=str(new_j.judgment_id),
            context_job_id=context_job_id,
        )
    JudgmentResult.objects.filter(
        table_id=prior_table_id, is_latest=True
    ).update(is_latest=False)


def ensure_mvp_judgment_result_for_table(
    *, table: TableScope, job: AnalysisJob
) -> JudgmentResult:
    """
    ``judgment_result`` を 1 行確保（同一 ``table``+``job`` は冪等）。

    002 スパイク: ``TableReadArtifact`` 観測から P0 / warnings / 薄い J2-TAX を合成する。
    ``read_artifact`` 行が無いときは空 ``cells`` として P0 に寄せる。

    新規挿入時のみ、**当該 ``table``** 上の既存 ``is_latest=True`` を False にしてから新行を latest にする。
    **rerun による別 ``table_id`` へ移ったときの旧 table の demote** は
    ``record_lineage_relations_after_materialize`` 内の
    ``_apply_judgment_supersedes_on_lineage`` が担当する。
    """
    existing = JudgmentResult.objects.filter(table=table, job=job).first()
    if existing is not None:
        return existing

    read = TableReadArtifact.objects.filter(table=table, job=job).first()
    if read is None:
        cells: dict = {}
        merges_list: list = []
        parse_warnings_list: list = []
    else:
        cells = read.cells if isinstance(read.cells, dict) else {}
        merges_list = read.merges if isinstance(read.merges, list) else []
        parse_warnings_list = (
            read.parse_warnings if isinstance(read.parse_warnings, list) else []
        )

    decision, taxonomy_code, evidence = build_judgment_from_read_observation(
        table,
        cells,
        merges_list,
        parse_warnings_list,
    )

    JudgmentResult.objects.filter(table=table, is_latest=True).update(is_latest=False)
    return JudgmentResult.objects.create(
        workspace_id=job.workspace_id,
        table=table,
        job=job,
        decision=decision,
        taxonomy_code=taxonomy_code,
        evidence=evidence,
        artifact_version=1,
        is_latest=True,
    )


def _mvp_read_artifact_cells_stub(table: TableScope) -> dict[str, object]:
    """
    001 暫定キー ``R{row}C{col}`` に寄せた最小 **稀疏 cells**（006 §5.4）。

    本格読取エンジン無し。bbox が揃うときは対角の 2 点のみ例示（格子復元ではない）。
    """
    cells: dict[str, object] = {
        "R0C0": {
            "raw_display": "",
            "r": 0,
            "c": 0,
            "_mvp_stub": True,
            "note": "001 MVP sparse placeholder; full read engine not run",
        }
    }
    if (
        table.row_min is not None
        and table.col_min is not None
        and table.row_max is not None
        and table.col_max is not None
    ):
        br = f"R{table.row_max}C{table.col_max}"
        if br != "R0C0":
            cells[br] = {
                "raw_display": "",
                "r": table.row_max,
                "c": table.col_max,
                "_mvp_stub": True,
            }
    return cells


def ensure_mvp_table_read_artifact_for_table(
    *, table: TableScope, job: AnalysisJob
) -> TableReadArtifact:
    """
    ``table_read_artifact`` を 1 行確保（同一 ``table``+``job`` は冪等）。

    新規挿入時のみ、**当該 ``table``** 上の既存 ``is_latest=True`` を False にしてから新行を latest にする。
    """
    existing = TableReadArtifact.objects.filter(table=table, job=job).first()
    if existing is not None:
        return existing
    TableReadArtifact.objects.filter(table=table, is_latest=True).update(is_latest=False)
    return TableReadArtifact.objects.create(
        workspace_id=job.workspace_id,
        table=table,
        job=job,
        cells=_mvp_read_artifact_cells_stub(table),
        merges=[],
        parse_warnings=[],
        artifact_version=1,
        is_latest=True,
    )


@transaction.atomic
def materialize_mvp_artifacts_for_job(
    *,
    job: AnalysisJob,
    requested_by: AbstractBaseUser | None = None,
) -> dict[str, str]:
    """
    014 ライフサイクル相当を **MVP 同期**で一通り生成する。

    ``job → table_scope → table_read_artifact → normalized_dataset → analysis_metadata →``
    ``judgment_result →`` （``dataset_payload`` に 002 ヒント・003 ``rows``/``trace_map`` を反映）→
    004 MVP が ``dataset_payload`` を参照入力として観測し ``decision`` / ``review_points`` に痕跡を付与 →
    ``confidence_evaluation → human_review_session → suggestion_set``

    001/003/004/002 の本番ロジックは走らせず、**責務境界を保ったプレースホルダ**のみ。
    ``004.decision`` と ``011.decision_recommendation`` は別フィールドで保持する。

    TODO: 非同期段階実行・001/002/003 実パイプライン。
    """
    if NormalizedDataset.objects.filter(job=job).exists():
        refs = _collect_artifact_refs_from_job(job)
        if refs.get("table_id"):
            scope = TableScope.objects.get(pk=refs["table_id"])
            ensure_mvp_table_read_artifact_for_table(table=scope, job=job)
            ensure_mvp_judgment_result_for_table(table=scope, job=job)
            if refs.get("dataset_id"):
                ds = NormalizedDataset.objects.get(pk=refs["dataset_id"])
                _apply_judgment_hints_to_normalized_dataset(dataset=ds, table=scope)
                meta = AnalysisMetadata.objects.filter(dataset=ds).first()
                if meta is not None:
                    apply_mvp_004_dataset_input_reflection(metadata=meta, dataset=ds)
        if refs.get("dataset_id"):
            _finalize_job_success(job, refs)
            record_lineage_relations_after_materialize(job=job, refs=refs)
        return refs

    scope = TableScope.objects.create(job=job, workspace_id=job.workspace_id)
    ensure_mvp_table_read_artifact_for_table(table=scope, job=job)
    dataset = NormalizedDataset.objects.create(
        job=job,
        table=scope,
        workspace_id=job.workspace_id,
        dataset_payload={
            "rows": [],
            "trace_map": [],
            "_mvp": True,
            "note": "003 MVP stub: not a real NormalizationResult",
        },
    )
    metadata = AnalysisMetadata.objects.create(
        dataset=dataset,
        workspace_id=job.workspace_id,
        review_required=True,
        review_points=[
            {
                "point_id": "mvp-1",
                "category": "MVP_PLACEHOLDER",
                "priority": 1,
            }
        ],
        dimensions=[{"id": "dim_row", "role": "identifier"}],
        measures=[{"id": "measure_value", "role": "metric"}],
        time_axis=None,
        decision={
            "block": "004-mvp-placeholder",
            "note": "004 meaning meta stub; not 002 Judgment.decision",
        },
    )
    ensure_mvp_judgment_result_for_table(table=scope, job=job)
    _apply_judgment_hints_to_normalized_dataset(dataset=dataset, table=scope)
    apply_mvp_004_dataset_input_reflection(metadata=metadata, dataset=dataset)
    evaluation = ConfidenceEvaluation.objects.create(
        metadata=metadata,
        workspace_id=job.workspace_id,
        confidence_score=0.72,
        risk_signals=[{"code": "mvp_stub", "severity": "info"}],
        decision_recommendation={
            "level": "review_optional",
            "source": "011-mvp-stub",
        },
    )
    session = create_review_session(metadata=metadata, created_by=requested_by)
    suggestion = create_suggestion_run_from_metadata(
        metadata=metadata,
        requested_by=requested_by,
        session_id=session.session_id,
    )
    refs = {
        "table_id": str(scope.table_id),
        "dataset_id": str(dataset.dataset_id),
        "metadata_id": str(metadata.metadata_id),
        "evaluation_ref": str(evaluation.evaluation_id),
        "session_id": str(session.session_id),
        "suggestion_run_ref": str(suggestion.suggestion_run_id),
    }
    _finalize_job_success(job, refs)
    record_lineage_relations_after_materialize(job=job, refs=refs)
    return refs


@transaction.atomic
def accept_or_create_analysis_job(
    *,
    workspace_id: str,
    idempotency_key: str | None,
    source_type: str = "",
    source_ref: str = "",
    request_payload: dict | None = None,
    requested_by: AbstractBaseUser | None = None,
) -> tuple[AnalysisJob, bool]:
    """
    ジョブ行を作成するか、同一 workspace + Idempotency-Key の既存行を返す。

    Returns:
        (job, created) — ``created`` が False のとき idempotent ヒット。
    """
    payload = request_payload if request_payload is not None else {}
    if idempotency_key:
        existing = (
            AnalysisJob.objects.select_for_update()
            .filter(workspace_id=workspace_id, idempotency_key=idempotency_key)
            .first()
        )
        if existing:
            return existing, False
        try:
            job = AnalysisJob.objects.create(
                workspace_id=workspace_id,
                idempotency_key=idempotency_key,
                source_type=source_type or "",
                source_ref=source_ref or "",
                request_payload=payload,
                status=JobStatus.PENDING,
                current_stage="queued",
                requested_by=requested_by,
            )
            return job, True
        except IntegrityError:
            hit = (
                AnalysisJob.objects.select_for_update()
                .filter(workspace_id=workspace_id, idempotency_key=idempotency_key)
                .first()
            )
            if hit:
                return hit, False
            raise

    job = AnalysisJob.objects.create(
        workspace_id=workspace_id,
        source_type=source_type or "",
        source_ref=source_ref or "",
        request_payload=payload,
        status=JobStatus.PENDING,
        current_stage="queued",
        requested_by=requested_by,
    )
    return job, True


def execute_mvp_pipeline_for_job(job_id: uuid.UUID) -> None:
    """
    MVP materialize のワーカー入口（同期テスト・RQ 双方から呼ぶ）。

    ``SUCCEEDED`` は冪等スキップ。``FAILED`` からの再実行は許容する。
    """
    with transaction.atomic():
        job = AnalysisJob.objects.select_for_update().get(pk=job_id)
        if job.status == JobStatus.SUCCEEDED:
            return
        now = timezone.now()
        job.status = JobStatus.RUNNING
        job.started_at = now
        job.current_stage = "mvp_materialize_running"
        job.error_code = ""
        job.error_message = ""
        job.save(
            update_fields=[
                "status",
                "started_at",
                "current_stage",
                "error_code",
                "error_message",
                "updated_at",
            ]
        )

    try:
        materialize_mvp_artifacts_for_job(job=job, requested_by=job.requested_by)
    except Exception as exc:  # noqa: BLE001 — MVP: persist worker failure
        with transaction.atomic():
            job = AnalysisJob.objects.select_for_update().get(pk=job_id)
            job.status = JobStatus.FAILED
            job.error_message = str(exc)[:2000]
            job.error_code = "MVP_MATERIALIZE_FAILED"
            job.completed_at = timezone.now()
            job.current_stage = "mvp_materialize_failed"
            job.save(
                update_fields=[
                    "status",
                    "error_message",
                    "error_code",
                    "completed_at",
                    "current_stage",
                    "updated_at",
                ]
            )


def create_analysis_job(
    *,
    workspace_id: str,
    source_type: str = "",
    source_ref: str = "",
    request_payload: dict | None = None,
    requested_by: AbstractBaseUser | None = None,
    current_stage: str = "requested",
) -> AnalysisJob:
    return AnalysisJob.objects.create(
        workspace_id=workspace_id,
        source_type=source_type or "",
        source_ref=source_ref or "",
        request_payload=request_payload if request_payload is not None else {},
        status=JobStatus.PENDING,
        current_stage=current_stage,
        requested_by=requested_by,
    )


def rerun_analysis_job(
    *,
    original: AnalysisJob,
    request_payload: dict | None,
    requested_by: AbstractBaseUser | None = None,
) -> AnalysisJob:
    """
    元ジョブをコピーして新規 AnalysisJob を作成する（MVP）。

    ``request_payload`` が ``None`` のときは ``original.request_payload`` を複製。
    辞書が渡された場合はそれを新ジョブの payload としてそのまま使う。
    いずれの場合も ``lineage`` をマージし、materialize 完了時に ``artifact_relation`` へ載せる。
    """
    new_payload = dict(
        original.request_payload if request_payload is None else request_payload
    )
    old_refs = _collect_artifact_refs_from_job(original)
    lineage: dict[str, str] = {
        "relation_type": LINEAGE_RELATION_JOB_RERUN,
        "prior_workspace_id": original.workspace_id,
        "source_job_id": str(original.job_id),
    }
    if old_refs.get("metadata_id"):
        lineage["prior_metadata_id"] = old_refs["metadata_id"]
    if old_refs.get("dataset_id"):
        lineage["prior_dataset_id"] = old_refs["dataset_id"]
    if old_refs.get("session_id"):
        lineage["prior_session_id"] = old_refs["session_id"]
    if old_refs.get("suggestion_run_ref"):
        lineage["prior_suggestion_run_id"] = old_refs["suggestion_run_ref"]
    if old_refs.get("table_id"):
        lineage["prior_table_id"] = old_refs["table_id"]
        jprev = JudgmentResult.objects.filter(
            table_id=old_refs["table_id"], is_latest=True
        ).first()
        if jprev:
            lineage["prior_judgment_id"] = str(jprev.judgment_id)
        rap = TableReadArtifact.objects.filter(
            table_id=old_refs["table_id"], is_latest=True
        ).first()
        if rap:
            lineage["prior_read_artifact_id"] = str(rap.artifact_id)
    new_payload["lineage"] = lineage
    return AnalysisJob.objects.create(
        workspace_id=original.workspace_id,
        source_type=original.source_type,
        source_ref=original.source_ref,
        request_payload=new_payload,
        status=JobStatus.PENDING,
        current_stage="rerun_requested",
        requested_by=requested_by,
    )


def _snapshot_review_points(metadata: AnalysisMetadata):
    rp = metadata.review_points
    if isinstance(rp, list):
        return list(rp)
    return rp


@transaction.atomic
def create_review_session(
    *,
    metadata: AnalysisMetadata,
    created_by: AbstractBaseUser | None = None,
) -> HumanReviewSession:
    """
    005 セッション作成: 004 の ``review_required`` / ``review_points`` を snapshot に取り込む正本の起点。

    解決・suppression 確定は行わない（OPEN のまま）。011/013 の値は書かない。
    """
    return HumanReviewSession.objects.create(
        metadata=metadata,
        workspace_id=metadata.workspace_id,
        state=ReviewSessionState.OPEN,
        review_required_snapshot=metadata.review_required,
        review_points_snapshot=_snapshot_review_points(metadata),
        created_by=created_by,
    )


@transaction.atomic
def submit_review_answers(
    *,
    session: HumanReviewSession,
    answers: list[dict],
    answered_by: AbstractBaseUser | None = None,
    mark_resolved: bool = False,
    resolution_grade: str | None = None,
) -> list[HumanReviewAnswer]:
    """
    回答を追加し、状態を簡易更新する（MVP）。

    TODO: suppression の自動生成（回答内容・信頼度に応じた SuppressionRecord 作成）は後続。
    """
    now = timezone.now()
    created: list[HumanReviewAnswer] = []
    for item in answers:
        created.append(
            HumanReviewAnswer.objects.create(
                session=session,
                question_key=item["question_key"],
                answer_value=item["answer_value"],
                answered_by=answered_by,
                answered_at=now,
            )
        )

    if session.state == ReviewSessionState.OPEN and answers:
        session.state = ReviewSessionState.IN_PROGRESS

    if mark_resolved:
        session.state = ReviewSessionState.RESOLVED

    if resolution_grade:
        session.resolution_grade = resolution_grade

    session.save(
        update_fields=[
            "state",
            "resolution_grade",
            "updated_at",
        ]
    )
    return created


def request_review_rerun(
    *,
    session: HumanReviewSession,
    requested_by: AbstractBaseUser | None = None,
) -> AnalysisJob:
    """
    005 文脈から upstream 再実行を **受理** する（MVP）。

    実際の 002/003/004 再処理・キュー投入は未実装（TODO）。
    """
    meta = session.metadata
    lineage: dict[str, str] = {
        "relation_type": LINEAGE_RELATION_REVIEW_RERUN,
        "prior_workspace_id": session.workspace_id,
        "rerun_from_session_id": str(session.session_id),
        "prior_metadata_id": str(meta.metadata_id),
        "prior_dataset_id": str(meta.dataset_id),
        "prior_session_id": str(session.session_id),
    }
    sugg = (
        SuggestionSet.objects.filter(metadata_id=meta.metadata_id)
        .order_by("-created_at")
        .first()
    )
    if sugg:
        lineage["prior_suggestion_run_id"] = str(sugg.suggestion_run_id)
    ds = meta.dataset
    if ds.table_id:
        tid = str(ds.table_id)
        lineage["prior_table_id"] = tid
        jprev = JudgmentResult.objects.filter(table_id=tid, is_latest=True).first()
        if jprev:
            lineage["prior_judgment_id"] = str(jprev.judgment_id)
        rap = TableReadArtifact.objects.filter(table_id=tid, is_latest=True).first()
        if rap:
            lineage["prior_read_artifact_id"] = str(rap.artifact_id)
    payload = {
        "trigger": "review_session_rerun",
        "rerun_from_session_id": str(session.session_id),
        "metadata_id": str(meta.metadata_id),
        "review_required_snapshot": session.review_required_snapshot,
        "review_points_snapshot": session.review_points_snapshot,
        "lineage": lineage,
    }
    return create_analysis_job(
        workspace_id=session.workspace_id,
        request_payload=payload,
        requested_by=requested_by,
        current_stage="review_upstream_rerun_requested",
    )


def _audit_suppression_from_session(session: HumanReviewSession | None) -> list[dict]:
    """005 ``SuppressionRecord`` を読み、013 の ``suppression_applied`` 監査ログ用に投影する（正本は移さない）。"""
    if session is None:
        return []
    out: list[dict] = []
    for rec in session.suppression_records.order_by("-created_at"):
        out.append(
            {
                "source": "review_suppression_record",
                "suppression_record_id": str(rec.id),
                "session_id": str(session.session_id),
                "suppression_level": rec.suppression_level,
                "suppression_reason": rec.suppression_reason,
            }
        )
    return out


_MAX_STUB_EVIDENCE_ITEMS_PER_LIST = 8


def _append_004_list_traces(evidence: list[dict], items: object, source_label: str) -> None:
    """``dimensions`` / ``measures`` の観測トレース（id/name の列挙に過ぎない。意味確定ではない）。"""
    if not isinstance(items, list) or not items:
        return
    for i, item in enumerate(items[:_MAX_STUB_EVIDENCE_ITEMS_PER_LIST]):
        if isinstance(item, dict):
            ref = item.get("id") or item.get("key") or f"index:{i}"
            row = {"source": source_label, "ref": str(ref)}
            name = item.get("name")
            if name is not None:
                row["note"] = f"name={name}"
            evidence.append(row)
        else:
            evidence.append(
                {"source": source_label, "ref": f"index:{i}", "note": "non-object element"}
            )


def _build_stub_analysis_candidates(metadata: AnalysisMetadata) -> list[dict]:
    """013 完全生成の前段スタブ。004 の ``measures`` 非空検知とメタ観測トレースのみ（011/005 は候補選定に使わない）。"""
    if not metadata.measures:
        return []
    evidence: list[dict] = [
        {"source": "004.metadata_id", "ref": str(metadata.metadata_id)},
    ]
    ds_id = metadata.dataset_id
    if ds_id:
        evidence.append({"source": "004.dataset_id", "ref": str(ds_id)})
    _append_004_list_traces(evidence, metadata.dimensions, "004.dimensions[]")
    _append_004_list_traces(evidence, metadata.measures, "004.measures[]")
    if metadata.time_axis is not None:
        evidence.append(
            {
                "source": "004.time_axis",
                "note": "present on metadata (observation only; not semantic lock-in)",
            }
        )
    risk_notes = [
        "MVP stub: full SuggestionGeneration (013) not implemented",
        "Stub trace: emitted because 004.measures is non-empty; category/priority/readiness/gating "
        "are not finalized. 005/011 do not select this candidate (see generation_constraints_reference on GET).",
    ]
    return [
        {
            "candidate_id": str(uuid.uuid4()),
            "category": "summary_stub",
            "priority": 0,
            "readiness": "low",
            "evidence": evidence,
            "risk_notes": risk_notes,
        }
    ]


@transaction.atomic
def create_suggestion_run_from_metadata(
    *,
    metadata: AnalysisMetadata,
    requested_by: AbstractBaseUser | None = None,
    dataset_id: uuid.UUID | None = None,
    evaluation_ref: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
) -> SuggestionSet:
    """
    013 suggestion run の MVP（同期生成）。

    TODO: 非同期ジョブ化・011 補助入力の本格統合・suppression クエリ別結果。
    """
    if metadata_is_superseded(metadata):
        raise StaleMetadataError()

    if dataset_id is not None and dataset_id != metadata.dataset_id:
        raise ValidationError("dataset_id does not match metadata.dataset_id")

    if evaluation_ref is not None:
        if not ConfidenceEvaluation.objects.filter(
            pk=evaluation_ref,
            metadata_id=metadata.metadata_id,
        ).exists():
            raise ValidationError("evaluation_ref does not belong to this metadata")

    if session_id is not None:
        session = (
            HumanReviewSession.objects.filter(
                pk=session_id,
                metadata_id=metadata.metadata_id,
            )
            .prefetch_related("suppression_records")
            .first()
        )
        if session is None:
            raise ValidationError("session_id does not belong to this metadata")
    else:
        session = (
            HumanReviewSession.objects.filter(metadata_id=metadata.metadata_id)
            .order_by("-created_at")
            .prefetch_related("suppression_records")
            .first()
        )

    table = metadata.dataset.table if metadata.dataset_id else None
    suppression_applied = _audit_suppression_from_session(session)
    analysis_candidates = _build_stub_analysis_candidates(metadata)

    return SuggestionSet.objects.create(
        metadata=metadata,
        workspace_id=metadata.workspace_id,
        table=table,
        analysis_candidates=analysis_candidates,
        suppression_applied=suppression_applied,
        created_by=requested_by,
    )
