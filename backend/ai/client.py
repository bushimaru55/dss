from __future__ import annotations

import os
from typing import Any

from openai import OpenAI


def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def ping_openai() -> dict[str, Any]:
    client = get_openai_client()
    models = client.models.list()
    ids = [m.id for m in models.data[:5]]
    return {
        "ok": True,
        "model_count": len(models.data),
        "sample_models": ids,
    }
