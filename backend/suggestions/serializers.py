from rest_framework import serializers

from suggestions.models import Suggestion


class SuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suggestion
        fields = (
            "id",
            "title",
            "description",
            "priority",
            "required_columns",
            "source",
            "created_at",
        )
        read_only_fields = fields
