from django.db import models

from datasets.models import Dataset, DatasetSheet, SemanticLabel


class SemanticMappingRun(models.Model):
    class Source(models.TextChoices):
        AI = "ai", "ai"
        USER = "user", "user"

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="semantic_runs")
    sheet = models.ForeignKey(DatasetSheet, on_delete=models.SET_NULL, null=True, blank=True, related_name="semantic_runs")
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.AI)
    created_at = models.DateTimeField(auto_now_add=True)


class SemanticMappingEntry(models.Model):
    run = models.ForeignKey(SemanticMappingRun, on_delete=models.CASCADE, related_name="entries")
    sheet = models.ForeignKey(DatasetSheet, on_delete=models.CASCADE, related_name="semantic_entries")
    column_name = models.CharField(max_length=512)
    semantic_label = models.CharField(max_length=32, choices=SemanticLabel.choices, default=SemanticLabel.UNKNOWN)
    confidence = models.FloatField(default=0.5)
    source = models.CharField(max_length=16, choices=SemanticMappingRun.Source.choices, default=SemanticMappingRun.Source.AI)
    created_at = models.DateTimeField(auto_now_add=True)
