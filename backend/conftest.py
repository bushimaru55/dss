from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from workspaces.models import Workspace


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username="tester",
        password="tester",
        email="tester@example.com",
        is_staff=True,
    )


@pytest.fixture
def auth_client(api_client: APIClient, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def workspace(user):
    return Workspace.objects.create(
        name="Test Workspace",
        slug="test-workspace",
        owner=user,
    )


@pytest.fixture(autouse=True)
def temp_media_root(settings):
    with tempfile.TemporaryDirectory() as tmp:
        settings.MEDIA_ROOT = Path(tmp)
        yield
