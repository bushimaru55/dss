from django.contrib import admin

from analysis_runs.models import AnalysisRun


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("question",)
