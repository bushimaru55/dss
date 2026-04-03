from django.db import models


class RagChunk(models.Model):
    source_type = models.CharField(max_length=32, default="manual")
    source_id = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    tokens = models.JSONField(default=list)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
