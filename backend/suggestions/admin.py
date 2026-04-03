from django.contrib import admin

from suggestions.models import Suggestion


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("title", "dataset", "priority", "source", "created_at")
    list_filter = ("priority", "source")
    search_fields = ("title", "description")
