from django.contrib import admin

from .models import Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug", "owner__username")
