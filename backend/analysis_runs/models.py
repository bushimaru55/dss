from django.db import models

from datasets.models import Dataset


class AnalysisRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="analysis_runs")
    question = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    plan_json = models.JSONField(default=dict, blank=True)
    result_json = models.JSONField(default=dict, blank=True)
    answer = models.TextField(blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(default=0.0)
    next_actions = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
