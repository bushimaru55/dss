from django.contrib import admin

from rag.models import RagChunk


@admin.register(RagChunk)
class RagChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "source_type", "source_id", "title", "created_at")
    search_fields = ("title", "content", "source_id")
    list_filter = ("source_type",)
