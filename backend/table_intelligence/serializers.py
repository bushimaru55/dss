"""
表解析 Jobs API 用 DTO（014 / OpenAPI 叩き台に沿った最小形）。

decision / decision_recommendation / evaluation_ref は Jobs 応答に含めない（別リソース）。
"""

from __future__ import annotations

from rest_framework import serializers

from table_intelligence.mvp_005_review_state import build_mvp_005_canonical_review_summary
from table_intelligence.mvp_011_evaluation_context import build_mvp_011_review_state_reference
from table_intelligence.mvp_013_suggestion_context import (
    build_mvp_013_generation_constraints_reference,
)
from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ConfidenceEvaluation,
    HumanReviewAnswer,
    HumanReviewSession,
    JudgmentResult,
    NormalizedDataset,
    SuggestionSet,
    SuppressionRecord,
    TableReadArtifact,
)


class StartAnalysisJobRequestSerializer(serializers.Serializer):
    workspace_id = serializers.CharField(max_length=255)
    source_type = serializers.CharField(max_length=64, required=False, allow_blank=True)
    source_ref = serializers.CharField(max_length=512, required=False, allow_blank=True)
    request_payload = serializers.JSONField(required=False)

    def validate(self, attrs: dict) -> dict:
        if "source_type" not in attrs:
            attrs["source_type"] = ""
        if "source_ref" not in attrs:
            attrs["source_ref"] = ""
        return attrs


class JobSummarySerializer(serializers.ModelSerializer):
    """受理・一覧用の最小サマリ。"""

    artifact_refs = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisJob
        fields = [
            "job_id",
            "workspace_id",
            "status",
            "current_stage",
            "created_at",
            "artifact_refs",
        ]

    def get_artifact_refs(self, obj: AnalysisJob):
        from table_intelligence.services import get_artifact_refs_for_job

        return get_artifact_refs_for_job(obj)


class JobDetailSerializer(serializers.ModelSerializer):
    artifact_refs = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisJob
        fields = [
            "job_id",
            "workspace_id",
            "idempotency_key",
            "source_type",
            "source_ref",
            "request_payload",
            "status",
            "current_stage",
            "error_code",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "requested_by_id",
            "artifact_refs",
        ]

    def get_artifact_refs(self, obj: AnalysisJob):
        from table_intelligence.services import get_artifact_refs_for_job

        return get_artifact_refs_for_job(obj)


class RerunJobRequestSerializer(serializers.Serializer):
    """body 省略時は元 job の request_payload を引き継ぐ（キー未指定のみ）。"""

    request_payload = serializers.JSONField(required=False)


class NormalizedDatasetSerializer(serializers.ModelSerializer):
    """003 正規化成果。``dataset_payload`` に rows / trace 等を格納可能（MVP）。"""

    job_id = serializers.SerializerMethodField()
    table_id = serializers.SerializerMethodField()

    class Meta:
        model = NormalizedDataset
        fields = [
            "dataset_id",
            "job_id",
            "table_id",
            "workspace_id",
            "schema_version",
            "dataset_payload",
            "created_at",
            "updated_at",
        ]

    def get_job_id(self, obj: NormalizedDataset) -> str | None:
        return str(obj.job_id) if obj.job_id else None

    def get_table_id(self, obj: NormalizedDataset) -> str | None:
        return str(obj.table_id) if obj.table_id else None


class AnalysisMetadataSerializer(serializers.ModelSerializer):
    """
    004 分析メタ。

    ``decision`` は 004 用 JSON のみ。011 の ``decision_recommendation`` は ConfidenceEvaluation 側。
    """

    dataset_id = serializers.UUIDField(source="dataset.dataset_id", read_only=True)

    class Meta:
        model = AnalysisMetadata
        fields = [
            "metadata_id",
            "dataset_id",
            "workspace_id",
            "review_required",
            "review_points",
            "dimensions",
            "measures",
            "time_axis",
            "decision",
            "created_at",
            "updated_at",
        ]


class CreateReviewSessionRequestSerializer(serializers.Serializer):
    metadata_id = serializers.UUIDField()


class HumanReviewSessionSerializer(serializers.ModelSerializer):
    metadata_id = serializers.UUIDField(source="metadata.metadata_id", read_only=True)
    mvp_005_canonical_summary = serializers.SerializerMethodField()

    class Meta:
        model = HumanReviewSession
        fields = [
            "session_id",
            "metadata_id",
            "workspace_id",
            "state",
            "review_required_snapshot",
            "review_points_snapshot",
            "resolution_grade",
            "mvp_005_canonical_summary",
            "created_by_id",
            "created_at",
            "updated_at",
        ]

    def get_mvp_005_canonical_summary(self, obj: HumanReviewSession) -> dict:
        return build_mvp_005_canonical_review_summary(obj)


class ReviewAnswerItemSerializer(serializers.Serializer):
    question_key = serializers.CharField(max_length=255)
    answer_value = serializers.JSONField()


class SubmitReviewAnswersRequestSerializer(serializers.Serializer):
    answers = ReviewAnswerItemSerializer(many=True)
    mark_resolved = serializers.BooleanField(required=False, default=False)
    resolution_grade = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class HumanReviewAnswerSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="session.session_id", read_only=True)

    class Meta:
        model = HumanReviewAnswer
        fields = [
            "id",
            "session_id",
            "question_key",
            "answer_value",
            "answered_by_id",
            "answered_at",
            "created_at",
            "updated_at",
        ]


class SuppressionRecordSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="session.session_id", read_only=True)

    class Meta:
        model = SuppressionRecord
        fields = [
            "id",
            "session_id",
            "workspace_id",
            "suppression_level",
            "suppression_reason",
            "suppressed_targets",
            "created_at",
            "updated_at",
        ]


class StartSuggestionRunRequestSerializer(serializers.Serializer):
    """OpenAPI ``StartSuggestionRunRequest`` 相当。主入力は ``metadata_id``。"""

    metadata_id = serializers.UUIDField()
    dataset_id = serializers.UUIDField(required=False, allow_null=True)
    evaluation_ref = serializers.UUIDField(required=False, allow_null=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)


class SuggestionSetSerializer(serializers.ModelSerializer):
    """
    006 / OpenAPI ``SuggestionSet`` の最小投影（``table_id`` は文字列）。

    ``generation_constraints_reference`` は 005 正本・011 補助への **読み取り参照**（提示確定ロジックなし）。
    """

    table_id = serializers.SerializerMethodField()
    metadata_id = serializers.UUIDField(source="metadata.metadata_id", read_only=True)
    generation_constraints_reference = serializers.SerializerMethodField()

    class Meta:
        model = SuggestionSet
        fields = [
            "suggestion_run_id",
            "table_id",
            "analysis_candidates",
            "suppression_applied",
            "metadata_id",
            "generation_constraints_reference",
            "created_at",
            "updated_at",
        ]

    def get_table_id(self, obj: SuggestionSet) -> str:
        return str(obj.table_id) if obj.table_id else ""

    def get_generation_constraints_reference(self, obj: SuggestionSet) -> dict:
        return build_mvp_013_generation_constraints_reference(obj)


class ConfidenceEvaluationSerializer(serializers.ModelSerializer):
    """
    011 評価。レスポンスでは API 名 ``evaluation_ref``（DB 列 ``evaluation_id`` と同一値）。

    ``decision_recommendation`` のみ。002/004 の ``decision`` は含めない。
    ``review_state_reference`` は同一 ``metadata`` の 005 正本サマリへの **読み取り参照**（上書きしない）。
    """

    evaluation_ref = serializers.UUIDField(source="evaluation_id", read_only=True)
    metadata_id = serializers.UUIDField(source="metadata.metadata_id", read_only=True)
    review_state_reference = serializers.SerializerMethodField()

    class Meta:
        model = ConfidenceEvaluation
        fields = [
            "evaluation_ref",
            "metadata_id",
            "workspace_id",
            "confidence_score",
            "risk_signals",
            "decision_recommendation",
            "review_state_reference",
            "created_at",
            "updated_at",
        ]

    def get_review_state_reference(self, obj: ConfidenceEvaluation) -> dict:
        return build_mvp_011_review_state_reference(obj.metadata)


class JudgmentResultSerializer(serializers.ModelSerializer):
    """
    006 / OpenAPI ``JudgmentResult`` の読み取り投影（``GET /tables/.../decision`` 差し替え用）。

    011 ``decision_recommendation`` は含めない。
    """

    class Meta:
        model = JudgmentResult
        fields = [
            "judgment_id",
            "table_id",
            "decision",
            "taxonomy_code",
            "evidence",
        ]


class TableReadArtifactSerializer(serializers.ModelSerializer):
    """006 / OpenAPI ``TableReadArtifact`` の読み取り投影（``GET /tables/.../read-artifact`` 差し替え用）。"""

    class Meta:
        model = TableReadArtifact
        fields = [
            "artifact_id",
            "table_id",
            "cells",
            "merges",
            "parse_warnings",
        ]
