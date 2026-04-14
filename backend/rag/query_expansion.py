"""RAG 検索クエリの同義語拡張・OpenAIリライト・任意HyDE。"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from ai.client import get_openai_api_key, get_openai_client

# (質問に含まれるときに検索語に追加するトークン群)
EXPANSIONS: list[tuple[str, list[str]]] = [
    ("営業", ["セールス", "sales", "担当"]),
    ("担当者", ["営業担当", "person", "rep"]),
    ("セールス", ["営業", "sales"]),
    ("売上", ["金額", "売上金額", "amount"]),
    ("顧客", ["取引先", "customer", "クライアント"]),
    ("取引先", ["顧客", "customer"]),
    ("ランキング", ["順位", "トップ", "一位", "上位"]),
    ("一位", ["トップ", "最大", "first"]),
    ("トップ", ["上位", "一位", "ランキング"]),
]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_一-龥ぁ-んァ-ン]{2,}")


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def expand_query_for_search(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return q
    extras: list[str] = []
    for needle, aliases in EXPANSIONS:
        if needle in q:
            extras.extend(aliases)
    if not extras:
        return q
    return f"{q} {' '.join(extras)}"


def should_use_hyde(query: str) -> bool:
    if not _bool_env("RAG_ENABLE_HYDE", default=False):
        return False
    q = (query or "").strip()
    tokens = _TOKEN_RE.findall(q)
    max_tokens = int(os.environ.get("RAG_HYDE_MAX_TOKENS", "4"))
    max_chars = int(os.environ.get("RAG_HYDE_MAX_CHARS", "24"))
    return len(tokens) <= max_tokens and len(q) <= max_chars


def rewrite_query_with_openai(query: str) -> str:
    q = (query or "").strip()
    if not q or not get_openai_api_key():
        return q
    if not _bool_env("RAG_ENABLE_QUERY_REWRITE", default=True):
        return q
    try:
        client = get_openai_client()
        model = os.environ.get("OPENAI_REWRITE_MODEL", os.environ.get("OPENAI_MODEL", "gpt-5-mini"))
        prompt = (
            "次のユーザー質問を、検索用クエリに最適化してください。"
            "意味を変えず、同義語を少量補い、30語以内の日本語中心のクエリを返してください。"
            "JSONで {\"search_query\":\"...\"} のみを返してください。"
            f"\nquestion={q}"
        )
        resp = client.responses.create(model=model, input=prompt, temperature=0)
        text = getattr(resp, "output_text", "") or ""
        data = json.loads(text)
        out = str(data.get("search_query", "")).strip()
        return out or q
    except Exception:
        return q


def generate_hypothetical_query_passage(query: str) -> str:
    q = (query or "").strip()
    if not q or not should_use_hyde(q) or not get_openai_api_key():
        return ""
    try:
        client = get_openai_client()
        model = os.environ.get("OPENAI_HYDE_MODEL", os.environ.get("OPENAI_MODEL", "gpt-5-mini"))
        prompt = (
            "以下の質問に対して、関連文書にありそうな短い説明文を120文字以内で作ってください。"
            "事実断定を避け、検索拡張のための一般的な記述にしてください。"
            f"\nquestion={q}"
        )
        resp = client.responses.create(model=model, input=prompt, temperature=0.2)
        return (getattr(resp, "output_text", "") or "").strip()
    except Exception:
        return ""


def prepare_search_query(query: str) -> dict[str, Any]:
    expanded = expand_query_for_search(query)
    rewritten = rewrite_query_with_openai(expanded)
    hyde = generate_hypothetical_query_passage(query)
    final_query = f"{rewritten} {hyde}".strip() if hyde else rewritten
    return {
        "original_query": (query or "").strip(),
        "expanded_query": expanded,
        "rewritten_query": rewritten,
        "hyde_text": hyde,
        "final_query": final_query or (query or "").strip(),
    }
