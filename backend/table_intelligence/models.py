"""
SPEC-TI-015 / DDL 叩き台に沿った表解析ドメインの ORM。

責務境界（正本）:
- 002 decision と 011 decision_recommendation は別概念・別カラム
- dataset_id と metadata_id は別成果物
- session_id のみ（review_session_id は不採用）

TODO: workspace_id は MVP では文字列保持。既存 workspaces.Workspace との対応（FK 化・slug・UUID）は後続で整理。
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class JobStatus(models.TextChoices):
    """MVP 用。DDL / 006 の完全列挙は後続 migration で整合。"""

    PENDING = "PENDING", "PENDING"
    RUNNING = "RUNNING", "RUNNING"
    SUCCEEDED = "SUCCEEDED", "SUCCEEDED"
    FAILED = "FAILED", "FAILED"
    CANCELED = "CANCELED", "CANCELED"


class AnalysisJob(models.Model):
    """
    実行ジョブ（014 実行 API / 015 §7.1 に相当）。

    成果物テーブル（table_read_artifact 等）とは分離する。
    """

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # TODO: 既存 Workspace モデルとの対応方式は後続で整理（FK 化 or slug 連携など）
    workspace_id = models.CharField(max_length=255)
    source_type = models.CharField(max_length=64, blank=True)
    source_ref = models.CharField(max_length=512, blank=True)
    status = models.CharField(
        max_length=32,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="table_intelligence_jobs",
    )
    request_payload = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=128, null=True, blank=True)
    current_stage = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis_job"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id", "status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace_id", "idempotency_key"],
                name="uniq_analysis_job_workspace_idempotency_key",
                condition=models.Q(idempotency_key__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        return f"AnalysisJob({self.job_id})"


class TableScope(models.Model):
    """
    観測対象テーブルのアンカー（001 / 015 §7.3）。

    bbox（row/col）は 0-based inclusive を前提（左上・右下を含む）。
    将来 table_read_artifact と 1:N で接続しやすいよう table_id を PK に維持する。
    """

    table_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        AnalysisJob,
        on_delete=models.CASCADE,
        related_name="table_scopes",
    )
    # TODO: 既存 Workspace モデルとの対応方式は後続で整理
    workspace_id = models.CharField(max_length=255)
    sheet_name = models.CharField(max_length=255, blank=True)
    table_label = models.CharField(max_length=255, blank=True)
    row_min = models.IntegerField(null=True, blank=True)
    col_min = models.IntegerField(null=True, blank=True)
    row_max = models.IntegerField(null=True, blank=True)
    col_max = models.IntegerField(null=True, blank=True)
    header_depth = models.IntegerField(null=True, blank=True)
    left_stub_depth = models.IntegerField(null=True, blank=True)
    detection_basis = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "table_scope"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["workspace_id"]),
        ]

    def __str__(self) -> str:
        return f"TableScope({self.table_id})"


TI_TABLE_UNKNOWN = "TI_TABLE_UNKNOWN"
"""002 / 009: 表種別が確定できない場合の暫定標準コード（006 `JudgmentResult.taxonomy_code`）。"""

# SPEC-TI-009 §6（002 は語彙を増やさずこれらのみを taxonomy_code に用いる）
TI_TABLE_LIST_DETAIL = "TI_TABLE_LIST_DETAIL"
TI_TABLE_CROSSTAB = "TI_TABLE_CROSSTAB"
TI_TABLE_FORM_REPORT = "TI_TABLE_FORM_REPORT"
TI_TABLE_PIVOT_LIKE = "TI_TABLE_PIVOT_LIKE"
TI_TABLE_TIME_SERIES = "TI_TABLE_TIME_SERIES"
TI_TABLE_LOOKUP_MATRIX = "TI_TABLE_LOOKUP_MATRIX"
TI_TABLE_KEY_VALUE = "TI_TABLE_KEY_VALUE"


class JudgmentDecision(models.TextChoices):
    """002 一次判定（006 §6 `decision`（Judgment）。011 `decision_recommendation` とは別）。"""

    AUTO_ACCEPT = "AUTO_ACCEPT", "AUTO_ACCEPT"
    NEEDS_REVIEW = "NEEDS_REVIEW", "NEEDS_REVIEW"
    REJECT = "REJECT", "REJECT"


class JudgmentResult(models.Model):
    """
    002 成果物（006 `JudgmentResult` / 015 §7.5）。

    ``decision_recommendation`` は持たない（011 は ``ConfidenceEvaluation``）。
    """

    judgment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_id = models.CharField(max_length=255)
    table = models.ForeignKey(
        TableScope,
        on_delete=models.CASCADE,
        related_name="judgment_results",
    )
    job = models.ForeignKey(
        AnalysisJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="judgment_results",
    )
    decision = models.CharField(max_length=32, choices=JudgmentDecision.choices)
    taxonomy_code = models.CharField(
        max_length=128,
        default=TI_TABLE_UNKNOWN,
        help_text="009 の TI_TABLE_*。未確定時は TI_TABLE_UNKNOWN。",
    )
    evidence = models.JSONField(
        default=list,
        blank=True,
        help_text="006 evidence[]（JSON 配列）。",
    )
    artifact_version = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "judgment_result"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
            models.Index(fields=["table", "is_latest"]),
            models.Index(fields=["job"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["table"],
                condition=models.Q(is_latest=True),
                name="uniq_judgment_result_latest_per_table",
            ),
        ]

    def __str__(self) -> str:
        return f"JudgmentResult({self.judgment_id})"


class TableReadArtifact(models.Model):
    """
    001 / 006 ``TableReadArtifact``（015 §7.4）。

    ``cells`` / ``merges`` / ``parse_warnings`` は JSON。大容量 offload は後続。
    """

    artifact_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_id = models.CharField(max_length=255)
    table = models.ForeignKey(
        TableScope,
        on_delete=models.CASCADE,
        related_name="read_artifacts",
    )
    job = models.ForeignKey(
        AnalysisJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="read_artifacts",
    )
    cells = models.JSONField(
        default=dict,
        blank=True,
        help_text="006 cells（001 稀疏表現など）。",
    )
    merges = models.JSONField(
        default=list,
        blank=True,
        help_text="006 merges[]。",
    )
    parse_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="006 parse_warnings[]（空配列可）。",
    )
    artifact_version = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "table_read_artifact"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
            models.Index(fields=["table", "is_latest"]),
            models.Index(fields=["job"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["table"],
                condition=models.Q(is_latest=True),
                name="uniq_table_read_artifact_latest_per_table",
            ),
        ]

    def __str__(self) -> str:
        return f"TableReadArtifact({self.artifact_id})"


class NormalizedDataset(models.Model):
    """
    003 正規化済みデータの器（015 §7.6）。

    ``rows`` / ``trace_map`` 相当は ``dataset_payload`` に集約（MVP）。
    """

    dataset_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        AnalysisJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="normalized_datasets",
    )
    table = models.ForeignKey(
        TableScope,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="normalized_datasets",
    )
    workspace_id = models.CharField(max_length=255)
    schema_version = models.CharField(max_length=64, default="0.1")
    dataset_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "normalized_dataset"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
            models.Index(fields=["job"]),
        ]

    def __str__(self) -> str:
        return f"NormalizedDataset({self.dataset_id})"


class AnalysisMetadata(models.Model):
    """
    004 分析メタ（015 §7.7）。suggestion の主入力 ``metadata_id`` の前提。

    ``decision`` は 004 ブロック用の **JSON**。002 Judgment の ``decision`` とは別概念（混同禁止）。
    """

    metadata_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.OneToOneField(
        NormalizedDataset,
        on_delete=models.CASCADE,
        related_name="analysis_metadata",
    )
    workspace_id = models.CharField(max_length=255)
    review_required = models.BooleanField(default=False)
    review_points = models.JSONField(default=list, blank=True)
    dimensions = models.JSONField(default=list, blank=True)
    measures = models.JSONField(default=list, blank=True)
    time_axis = models.JSONField(null=True, blank=True)
    decision = models.JSONField(
        default=dict,
        blank=True,
        help_text="004 用。002 Judgment の decision とは別フィールド。",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analysis_metadata"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
        ]

    def __str__(self) -> str:
        return f"AnalysisMetadata({self.metadata_id})"


class ConfidenceEvaluation(models.Model):
    """
    011 信頼度評価（015 §7.10）。API パスは ``evaluation_ref``、DB PK は ``evaluation_id``（同一キー空間）。

    ``decision_recommendation`` のみ保持し、002 の ``decision`` は持たない。
    GET 応答の ``review_state_reference`` は ``mvp_011_evaluation_context`` による 005 参照（正本は HumanReviewSession）。
    """

    evaluation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata = models.ForeignKey(
        AnalysisMetadata,
        on_delete=models.CASCADE,
        related_name="confidence_evaluations",
    )
    workspace_id = models.CharField(max_length=255)
    confidence_score = models.FloatField(default=0.0)
    risk_signals = models.JSONField(default=list, blank=True)
    decision_recommendation = models.JSONField(
        default=dict,
        blank=True,
        help_text="011 の推奨ブロック。002 decision とは別。",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "confidence_evaluation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
            models.Index(fields=["metadata"]),
        ]

    def __str__(self) -> str:
        return f"ConfidenceEvaluation({self.evaluation_id})"


class ReviewSessionState(models.TextChoices):
    """005 人確認の最小状態。完全な遷移は後続で拡張。"""

    OPEN = "OPEN", "OPEN"
    IN_PROGRESS = "IN_PROGRESS", "IN_PROGRESS"
    RESOLVED = "RESOLVED", "RESOLVED"
    CLOSED_UNRESOLVED = "CLOSED_UNRESOLVED", "CLOSED_UNRESOLVED"


class SuppressionLevel(models.TextChoices):
    SUGGESTION_BLOCKED = "SUGGESTION_BLOCKED", "SUGGESTION_BLOCKED"
    SUGGESTION_LIMITED = "SUGGESTION_LIMITED", "SUGGESTION_LIMITED"
    SUGGESTION_ALLOWED_WITH_CAUTION = (
        "SUGGESTION_ALLOWED_WITH_CAUTION",
        "SUGGESTION_ALLOWED_WITH_CAUTION",
    )


class HumanReviewSession(models.Model):
    """
    005 人確認セッション。正本 ID は ``session_id`` のみ（review_session_id は不採用）。

    snapshot 列で作成時点の 004 ``review_required`` / ``review_points`` を保持する。
    API 応答の ``mvp_005_canonical_summary`` は ``mvp_005_review_state`` で観測のみ組立（011/013 と分離）。
    """

    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata = models.ForeignKey(
        AnalysisMetadata,
        on_delete=models.CASCADE,
        related_name="human_review_sessions",
    )
    workspace_id = models.CharField(max_length=255)
    state = models.CharField(
        max_length=32,
        choices=ReviewSessionState.choices,
        default=ReviewSessionState.OPEN,
    )
    review_required_snapshot = models.BooleanField(default=False)
    review_points_snapshot = models.JSONField(default=list, blank=True)
    resolution_grade = models.CharField(max_length=64, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_review_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "human_review_session"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
            models.Index(fields=["metadata"]),
        ]

    def __str__(self) -> str:
        return f"HumanReviewSession({self.session_id})"


class HumanReviewAnswer(models.Model):
    """1 問 1 行。複数件は answers API でまとめて追加可能。"""

    session = models.ForeignKey(
        HumanReviewSession,
        on_delete=models.CASCADE,
        related_name="answer_rows",
    )
    question_key = models.CharField(max_length=255)
    answer_value = models.JSONField(default=dict, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="human_review_answers",
    )
    answered_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "human_review_answer"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session"]),
        ]

    def __str__(self) -> str:
        return f"HumanReviewAnswer({self.pk})"


class SuppressionRecord(models.Model):
    """
    005 suppression の DB 保持（正本）。suggestion 側へ正本を移さない。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        HumanReviewSession,
        on_delete=models.CASCADE,
        related_name="suppression_records",
    )
    workspace_id = models.CharField(max_length=255)
    suppression_level = models.CharField(max_length=64, choices=SuppressionLevel.choices)
    suppression_reason = models.TextField(blank=True)
    suppressed_targets = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suppression_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session"]),
            models.Index(fields=["workspace_id"]),
        ]

    def __str__(self) -> str:
        return f"SuppressionRecord({self.id})"


class SuggestionSet(models.Model):
    """
    013 成果物（015 §7.11 方針 A）。

    ``analysis_candidates`` は MVP では JSON 一括保持（``suggestion_candidate`` テーブルは後続）。
    ``suppression_applied`` は生成時に **005 の SuppressionRecord を読んだ監査ログ**であり、
    suppression の正本は review 側のまま（ここへ正本を移さない）。
    API の ``generation_constraints_reference`` は ``mvp_013_suggestion_context`` による 005/011 参照（制御確定なし）。
    """

    suggestion_run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metadata = models.ForeignKey(
        AnalysisMetadata,
        on_delete=models.CASCADE,
        related_name="suggestion_sets",
    )
    workspace_id = models.CharField(max_length=255)
    table = models.ForeignKey(
        TableScope,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggestion_sets",
    )
    analysis_candidates = models.JSONField(default=list, blank=True)
    suppression_applied = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_suggestion_sets",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suggestion_set"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id"]),
            models.Index(fields=["metadata"]),
        ]

    def __str__(self) -> str:
        return f"SuggestionSet({self.suggestion_run_id})"


class ArtifactRelation(models.Model):
    """
    lineage / rerun 監査（015 §7.14）。

    多型参照は文字列で保持し、FK は張らない（MVP）。
    """

    relation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_id = models.CharField(max_length=255, db_index=True)
    relation_type = models.CharField(max_length=64, db_index=True)
    from_artifact_type = models.CharField(max_length=64)
    from_artifact_id = models.CharField(max_length=64)
    to_artifact_type = models.CharField(max_length=64)
    to_artifact_id = models.CharField(max_length=64)
    context_job_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="この edge を記録した成果物生成ジョブ（任意・FK なし）",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "artifact_relation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace_id", "relation_type", "created_at"]),
            models.Index(fields=["from_artifact_type", "from_artifact_id"]),
            models.Index(fields=["to_artifact_type", "to_artifact_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "context_job_id",
                    "relation_type",
                    "from_artifact_type",
                    "from_artifact_id",
                    "to_artifact_type",
                    "to_artifact_id",
                ],
                name="uniq_artifact_relation_edge_per_job",
            ),
        ]

    def __str__(self) -> str:
        return f"ArtifactRelation({self.relation_id})"
