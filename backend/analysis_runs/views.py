from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from analysis_runs.models import AnalysisRun
from analysis_runs.serializers import AnalysisRunSerializer, ChatAskSerializer
from analysis_runs.tasks import run_analysis_job
from datasets.models import Dataset


class ChatAskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChatAskSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        dataset = Dataset.objects.get(id=ser.validated_data["dataset_id"], workspace__owner=request.user)
        run = AnalysisRun.objects.create(dataset=dataset, question=ser.validated_data["question"])
        run_analysis_job.delay(run.id)
        return Response(
            {"analysis_run_id": run.id, "status": run.status},
            status=status.HTTP_202_ACCEPTED,
        )


class ChatAskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id: int):
        run = AnalysisRun.objects.select_related("dataset").filter(
            id=run_id,
            dataset__workspace__owner=request.user,
        ).first()
        if not run:
            return Response({"detail": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(AnalysisRunSerializer(run).data)
