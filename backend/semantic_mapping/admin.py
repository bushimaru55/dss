from django.contrib import admin

from semantic_mapping.models import SemanticMappingEntry, SemanticMappingRun


@admin.register(SemanticMappingRun)
class SemanticMappingRunAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "sheet", "source", "created_at")
    list_filter = ("source",)


@admin.register(SemanticMappingEntry)
class SemanticMappingEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "column_name", "semantic_label", "confidence", "source")
    search_fields = ("column_name",)
