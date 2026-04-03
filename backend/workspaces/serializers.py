from __future__ import annotations

import secrets

from django.utils.text import slugify
from rest_framework import serializers

from .models import Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ("id", "name", "slug", "owner", "created_at")
        read_only_fields = ("id", "slug", "owner", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        name = validated_data["name"]
        base = slugify(name) or "workspace"
        slug = base
        while Workspace.objects.filter(slug=slug).exists():
            slug = f"{base}-{secrets.token_hex(3)}"
        return Workspace.objects.create(
            name=name,
            slug=slug,
            owner=request.user,
        )
