from django.db import models

from datasets.models import Dataset, DatasetSheet


class ProfilingRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "queued"
        RUNNING = "running", "running"
        SUCCEEDED = "succeeded", "succeeded"
        FAILED = "failed", "failed"

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="profiling_runs")
    sheet = models.ForeignKey(DatasetSheet, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiling_runs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProfiledColumn(models.Model):
    run = models.ForeignKey(ProfilingRun, on_delete=models.CASCADE, related_name="columns")
    sheet = models.ForeignKey(DatasetSheet, on_delete=models.CASCADE, related_name="profiled_columns")
    original_name = models.CharField(max_length=512)
    normalized_name = models.CharField(max_length=512)
    inferred_dtype = models.CharField(max_length=32)
    null_ratio = models.FloatField(default=0.0)
    unique_ratio = models.FloatField(default=0.0)
    sample_values = models.JSONField(default=list)
    warnings = models.JSONField(default=list)
