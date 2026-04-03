from django.contrib import admin

from profiling.models import ProfiledColumn, ProfilingRun


@admin.register(ProfilingRun)
class ProfilingRunAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "sheet", "status", "updated_at")
    list_filter = ("status",)


@admin.register(ProfiledColumn)
class ProfiledColumnAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "original_name", "inferred_dtype")
    search_fields = ("original_name", "normalized_name")
