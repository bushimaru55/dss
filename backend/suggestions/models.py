from django.db import models

from datasets.models import Dataset


class SuggestionSource(models.TextChoices):
    RULE = "rule", "rule"
    AI = "ai", "ai"


class SuggestionPriority(models.TextChoices):
    LOW = "low", "low"
    MEDIUM = "medium", "medium"
    HIGH = "high", "high"


class Suggestion(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="suggestions",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(
        max_length=16,
        choices=SuggestionPriority.choices,
        default=SuggestionPriority.MEDIUM,
    )
    required_columns = models.JSONField(default=list)
    source = models.CharField(
        max_length=16,
        choices=SuggestionSource.choices,
        default=SuggestionSource.RULE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return self.title
