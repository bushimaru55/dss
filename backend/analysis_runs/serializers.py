from rest_framework import serializers

from analysis_runs.models import AnalysisRun
from datasets.models import Dataset


class ChatAskSerializer(serializers.Serializer):
    dataset_id = serializers.IntegerField()
    question = serializers.CharField(max_length=4000)

    def validate_dataset_id(self, value: int) -> int:
        request = self.context["request"]
        ok = Dataset.objects.filter(id=value, workspace__owner=request.user).exists()
        if not ok:
            raise serializers.ValidationError("dataset not found")
        return value


class AnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisRun
        fields = (
            "id",
            "dataset",
            "question",
            "status",
            "plan_json",
            "result_json",
            "answer",
            "evidence",
            "confidence",
            "next_actions",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
