"""
表解析 Jobs API（DRF APIView）。

workspace スコープ: ``table_intelligence.workspace_scope``（014 §14.3 404 マスク）。
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from table_intelligence.models import (
    AnalysisJob,
    AnalysisMetadata,
    ConfidenceEvaluation,
    HumanReviewSession,
    NormalizedDataset,
    SuggestionSet,
    SuppressionRecord,
    TableScope,
)
from table_intelligence.serializers import (
    AnalysisMetadataSerializer,
    ConfidenceEvaluationSerializer,
    CreateReviewSessionRequestSerializer,
    HumanReviewAnswerSerializer,
    HumanReviewSessionSerializer,
    JobDetailSerializer,
    JobSummarySerializer,
    NormalizedDatasetSerializer,
    RerunJobRequestSerializer,
    StartAnalysisJobRequestSerializer,
    StartSuggestionRunRequestSerializer,
    SubmitReviewAnswersRequestSerializer,
    SuggestionSetSerializer,
    SuppressionRecordSerializer,
)
from table_intelligence.pipeline import parse_idempotency_key, schedule_mvp_pipeline
from table_intelligence.exceptions import StaleMetadataConflict
from table_intelligence.services import (
    StaleMetadataError,
    accept_or_create_analysis_job,
    create_review_session,
    create_suggestion_run_from_metadata,
    get_artifact_ref_bundles_for_table,
    get_latest_artifact_refs_for_table,
    get_latest_judgment_result_for_table,
    get_latest_table_read_artifact_for_table,
    judgment_result_to_judgment_api_dict,
    rerun_analysis_job,
    request_review_rerun,
    submit_review_answers,
    table_read_artifact_to_api_dict,
)
from table_intelligence.workspace_scope import require_workspace_access, scoped_filter


class TableScopeSummaryView(APIView):
    """GET /tables/<table_id>/ — ``TableSummary``（014 / OpenAPI）。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(
            scoped_filter(TableScope.objects.select_related("job"), request.user),
            pk=table_id,
        )
        return Response(
            {
                "table_id": str(table.table_id),
                "refs": get_latest_artifact_refs_for_table(table),
            },
            status=status.HTTP_200_OK,
        )


class TableReadArtifactView(APIView):
    """GET /tables/<table_id>/read-artifact/ — ``table_read_artifact`` の latest 行（006）。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(
            scoped_filter(TableScope.objects.all(), request.user),
            pk=table_id,
        )
        row = get_latest_table_read_artifact_for_table(table)
        if row is None:
            raise Http404()
        return Response(
            table_read_artifact_to_api_dict(row),
            status=status.HTTP_200_OK,
        )


class TableJudgmentDetailView(APIView):
    """GET /tables/<table_id>/decision/ — 002 ``JudgmentResult``（``judgment_result`` 最新行）。011 と混在しない。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(
            scoped_filter(TableScope.objects.all(), request.user),
            pk=table_id,
        )
        row = get_latest_judgment_result_for_table(table)
        if row is None:
            raise Http404()
        return Response(
            judgment_result_to_judgment_api_dict(row),
            status=status.HTTP_200_OK,
        )


class TableArtifactRefsListView(APIView):
    """GET /tables/<table_id>/artifacts/ — ``ArtifactRefsList``。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(
            scoped_filter(TableScope.objects.all(), request.user),
            pk=table_id,
        )
        items = get_artifact_ref_bundles_for_table(table)
        return Response({"items": items}, status=status.HTTP_200_OK)


class AnalysisMetadataReviewPointsView(APIView):
    """GET /metadata/<metadata_id>/review-points/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, metadata_id, *args, **kwargs):
        meta = get_object_or_404(
            scoped_filter(
                AnalysisMetadata.objects.select_related("dataset"),
                request.user,
            ),
            pk=metadata_id,
        )
        return Response(
            {
                "metadata_id": str(meta.metadata_id),
                "review_points": list(meta.review_points),
            },
            status=status.HTTP_200_OK,
        )


class TableAnalysisJobCreateView(APIView):
    """POST /table-analysis/jobs/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        ser = StartAnalysisJobRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        require_workspace_access(request.user, data["workspace_id"])
        idempotency_key = parse_idempotency_key(request)
        job, created = accept_or_create_analysis_job(
            workspace_id=data["workspace_id"],
            idempotency_key=idempotency_key,
            source_type=data.get("source_type") or "",
            source_ref=data.get("source_ref") or "",
            request_payload=data.get("request_payload"),
            requested_by=request.user,
        )
        if created:
            schedule_mvp_pipeline(job.job_id)
        job.refresh_from_db()
        out = JobSummarySerializer(job)
        status_code = (
            status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
        )
        return Response(out.data, status=status_code)


class TableAnalysisJobDetailView(APIView):
    """GET /table-analysis/jobs/<job_id>/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id, *args, **kwargs):
        job = get_object_or_404(scoped_filter(AnalysisJob.objects.all(), request.user), pk=job_id)
        return Response(JobDetailSerializer(job).data)


class TableAnalysisJobRerunView(APIView):
    """POST /table-analysis/jobs/<job_id>/rerun/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id, *args, **kwargs):
        original = get_object_or_404(scoped_filter(AnalysisJob.objects.all(), request.user), pk=job_id)
        ser = RerunJobRequestSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)
        payload = (
            ser.validated_data["request_payload"]
            if "request_payload" in ser.validated_data
            else None
        )
        new_job = rerun_analysis_job(
            original=original,
            request_payload=payload,
            requested_by=request.user,
        )
        return Response(
            JobSummarySerializer(new_job).data,
            status=status.HTTP_201_CREATED,
        )


class NormalizedDatasetDetailView(APIView):
    """GET /datasets/<dataset_id>/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, dataset_id, *args, **kwargs):
        ds = get_object_or_404(scoped_filter(NormalizedDataset.objects.all(), request.user), pk=dataset_id)
        return Response(NormalizedDatasetSerializer(ds).data)


class AnalysisMetadataDetailView(APIView):
    """GET /metadata/<metadata_id>/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, metadata_id, *args, **kwargs):
        meta = get_object_or_404(
            scoped_filter(
                AnalysisMetadata.objects.select_related("dataset"),
                request.user,
            ),
            pk=metadata_id,
        )
        return Response(AnalysisMetadataSerializer(meta).data)


class ConfidenceEvaluationDetailView(APIView):
    """
    GET /evaluations/<evaluation_ref>/

    URL パラメータ名は ``evaluation_ref`` だが、DB PK ``evaluation_id`` と同一キー空間。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, evaluation_ref, *args, **kwargs):
        ev = get_object_or_404(
            scoped_filter(
                ConfidenceEvaluation.objects.select_related("metadata"),
                request.user,
            ),
            pk=evaluation_ref,
        )
        return Response(ConfidenceEvaluationSerializer(ev).data)


class ReviewSessionCreateView(APIView):
    """POST /review-sessions/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        ser = CreateReviewSessionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        metadata = get_object_or_404(
            scoped_filter(
                AnalysisMetadata.objects.select_related("dataset"),
                request.user,
            ),
            pk=ser.validated_data["metadata_id"],
        )
        session = create_review_session(metadata=metadata, created_by=request.user)
        return Response(
            HumanReviewSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class ReviewSessionDetailView(APIView):
    """GET /review-sessions/<session_id>/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(
            scoped_filter(
                HumanReviewSession.objects.select_related("metadata"),
                request.user,
            ),
            pk=session_id,
        )
        return Response(HumanReviewSessionSerializer(session).data)


class ReviewSessionRerunView(APIView):
    """POST /review-sessions/<session_id>/rerun/ — 014 / OpenAPI ``rerunAfterReview`` 相当の受理口（MVP）。"""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(
            scoped_filter(
                HumanReviewSession.objects.select_related("metadata"),
                request.user,
            ),
            pk=session_id,
        )
        job = request_review_rerun(session=session, requested_by=request.user)
        return Response(
            JobSummarySerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )


class ReviewSessionAnswersView(APIView):
    """POST /review-sessions/<session_id>/answers/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(scoped_filter(HumanReviewSession.objects.all(), request.user), pk=session_id)
        ser = SubmitReviewAnswersRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        answers_payload = [dict(a) for a in v["answers"]]
        created = submit_review_answers(
            session=session,
            answers=answers_payload,
            answered_by=request.user,
            mark_resolved=v.get("mark_resolved") or False,
            resolution_grade=v.get("resolution_grade") or None,
        )
        session.refresh_from_db()
        return Response(
            {
                "session": HumanReviewSessionSerializer(session).data,
                "answers": HumanReviewAnswerSerializer(created, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class ReviewSessionSuppressionView(APIView):
    """GET /review-sessions/<session_id>/suppression/ — 無ければ空配列。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(scoped_filter(HumanReviewSession.objects.all(), request.user), pk=session_id)
        qs = SuppressionRecord.objects.filter(session=session).order_by("-created_at")
        return Response(
            SuppressionRecordSerializer(qs, many=True).data,
            status=status.HTTP_200_OK,
        )


class SuggestionRunStartView(APIView):
    """POST /suggestion-runs/ — 013 / OpenAPI ``startSuggestionRun``（MVP・同期生成）。"""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        ser = StartSuggestionRunRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        metadata = get_object_or_404(
            scoped_filter(
                AnalysisMetadata.objects.select_related("dataset", "dataset__table"),
                request.user,
            ),
            pk=data["metadata_id"],
        )
        try:
            sset = create_suggestion_run_from_metadata(
                metadata=metadata,
                requested_by=request.user,
                dataset_id=data.get("dataset_id"),
                evaluation_ref=data.get("evaluation_ref"),
                session_id=data.get("session_id"),
            )
        except StaleMetadataError:
            raise StaleMetadataConflict() from None
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict") and exc.message_dict:
                raise DRFValidationError(detail=exc.message_dict) from exc
            raise DRFValidationError(detail=list(exc.messages)) from exc
        return Response(
            {
                "suggestion_run_ref": str(sset.suggestion_run_id),
                "job_id": None,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class SuggestionSetDetailView(APIView):
    """GET /suggestion-runs/<suggestion_run_ref>/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, suggestion_run_ref, *args, **kwargs):
        sset = get_object_or_404(
            scoped_filter(
                SuggestionSet.objects.select_related("metadata", "table"),
                request.user,
            ),
            pk=suggestion_run_ref,
        )
        return Response(SuggestionSetSerializer(sset).data)


class SuggestionCandidatesListView(APIView):
    """GET /suggestion-runs/<suggestion_run_ref>/candidates/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, suggestion_run_ref, *args, **kwargs):
        sset = get_object_or_404(
            scoped_filter(
                SuggestionSet.objects.select_related("metadata"),
                request.user,
            ),
            pk=suggestion_run_ref,
        )
        body: dict = {"candidates": list(sset.analysis_candidates)}
        if request.query_params.get("include") == "recommendation":
            ev = (
                scoped_filter(ConfidenceEvaluation.objects.all(), request.user)
                .filter(metadata_id=sset.metadata_id)
                .order_by("-created_at")
                .first()
            )
            if ev is not None:
                body["decision_recommendation"] = ev.decision_recommendation
        return Response(body, status=status.HTTP_200_OK)
