from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


def get_openai_api_key() -> str:
    env = os.environ.get("OPENAI_API_KEY", "").strip()
    if env:
        return env
    try:
        from ai.models import OpenAISettings

        row = OpenAISettings.objects.filter(pk=1).first()
        if row and row.api_key:
            return row.api_key.strip()
    except Exception:
        pass
    return ""


def get_openai_client() -> OpenAI:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured (環境変数または管理画面の API キー設定)")

    return _make_openai_client(api_key=api_key)


def _make_openai_client(*, api_key: str) -> OpenAI:
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def ping_openai_with_key(api_key: str) -> dict[str, Any]:
    """指定キーで OpenAI API に接続し、モデル一覧取得で疎通確認する。"""
    key = api_key.strip()
    if not key:
        raise ValueError("API キーが空です")
    client = _make_openai_client(api_key=key)
    models = client.models.list()
    data = getattr(models, "data", None) or []
    ids = [m.id for m in data[:5]]
    return {
        "ok": True,
        "model_count": len(data),
        "sample_models": ids,
    }


def ping_openai() -> dict[str, Any]:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured (環境変数または管理画面の API キー設定)")
    return ping_openai_with_key(api_key)
