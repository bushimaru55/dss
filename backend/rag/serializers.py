from rest_framework import serializers


class RagIndexDocumentSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    source_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content = serializers.CharField()
    metadata = serializers.JSONField(required=False)


class RagIndexSerializer(serializers.Serializer):
    source_type = serializers.CharField(max_length=32, default="manual")
    replace_scope = serializers.CharField(max_length=255, required=False, allow_blank=True)
    documents = RagIndexDocumentSerializer(many=True)


class RagSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
