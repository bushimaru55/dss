from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from ai.admin import _extract_api_key_from_post
from ai.client import get_openai_api_key, ping_openai_with_key
from ai.models import OpenAISettings


def test_extract_api_key_from_post_plain():
    req = RequestFactory().post("/", {"api_key": " sk ", "_test_key": "1"})
    assert _extract_api_key_from_post(req) == "sk"


def test_extract_api_key_from_post_prefixed():
    req = RequestFactory().post("/", {"foo-api_key": "abc", "_test_key": "1"})
    assert _extract_api_key_from_post(req) == "abc"


@pytest.mark.django_db
def test_get_openai_api_key_prefers_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    OpenAISettings.objects.get_or_create(pk=1, defaults={"api_key": "sk-from-db"})
    assert get_openai_api_key() == "sk-from-env"


@pytest.mark.django_db
def test_get_openai_api_key_falls_back_to_db(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    obj, _ = OpenAISettings.objects.get_or_create(pk=1)
    obj.api_key = "sk-from-db"
    obj.save()
    assert get_openai_api_key() == "sk-from-db"


def test_ping_openai_with_key_empty_raises():
    with pytest.raises(ValueError):
        ping_openai_with_key("  ")


@patch("ai.client._make_openai_client")
def test_ping_openai_with_key_success(mock_make):
    mock_client = MagicMock()
    mock_make.return_value = mock_client
    m1 = MagicMock()
    m1.id = "gpt-4o-mini"
    mock_client.models.list.return_value = MagicMock(data=[m1])
    out = ping_openai_with_key("sk-test")
    assert out["ok"] is True
    assert out["model_count"] == 1
    assert out["sample_models"] == ["gpt-4o-mini"]
