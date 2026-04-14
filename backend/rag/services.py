from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ai.client import get_openai_api_key, get_openai_client
from rag.models import RagChunk
from rag.query_expansion import prepare_search_query


_TOKEN_RE = re.compile(r"[A-Za-z0-9_一-龥ぁ-んァ-ン]{2,}")
_CJK_RE = re.compile(r"[一-龥ぁ-んァ-ン]+")


def tokenize(text: str) -> list[str]:
    raw = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    extra: list[str] = []
    for seg in _CJK_RE.findall(text or ""):
        s = seg.strip()
        if len(s) < 2:
            continue
        # add bi-gram tokens for better Japanese partial match
        for i in range(0, len(s) - 1):
            extra.append(s[i : i + 2])
    return raw + extra


def _chunk_text(text: str, max_chars: int = 1000, overlap: int = 120) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    out: list[str] = []
    i = 0
    while i < len(text):
        out.append(text[i : i + max_chars])
        if i + max_chars >= len(text):
            break
        i += max_chars - overlap
    return out


def index_documents(docs: list[dict[str, Any]], source_type: str = "manual", replace_scope: str | None = None) -> int:
    if replace_scope:
        RagChunk.objects.filter(source_type=source_type, source_id=replace_scope).delete()
    created = 0
    for d in docs:
        title = str(d.get("title") or "untitled")
        source_id = str(d.get("source_id") or "")
        metadata = d.get("metadata") or {}
        for idx, part in enumerate(_chunk_text(str(d.get("content") or ""))):
            tokens = tokenize(part)
            if not tokens:
                continue
            RagChunk.objects.create(
                source_type=source_type,
                source_id=source_id,
                title=title,
                content=part,
                tokens=tokens,
                metadata={**metadata, "chunk_index": idx},
            )
            created += 1
    return created


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _rank_map(scores: list[tuple[int, float]]) -> dict[int, int]:
    ranked = sorted(scores, key=lambda x: x[1], reverse=True)
    return {chunk_id: idx + 1 for idx, (chunk_id, _) in enumerate(ranked)}


def _embed_texts(texts: list[str]) -> list[list[float]] | None:
    if not texts or not get_openai_api_key():
        return None
    try:
        client = get_openai_client()
        model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        resp = client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]
    except Exception:
        return None


def _apply_rrf(
    text_ranks: dict[int, int],
    dense_ranks: dict[int, int],
    text_weight: float,
    dense_weight: float,
    rrf_k: int = 60,
) -> dict[int, float]:
    ids = set(text_ranks) | set(dense_ranks)
    out: dict[int, float] = {}
    for cid in ids:
        score = 0.0
        rt = text_ranks.get(cid)
        rd = dense_ranks.get(cid)
        if rt:
            score += text_weight / (rrf_k + rt)
        if rd:
            score += dense_weight / (rrf_k + rd)
        out[cid] = score
    return out


def _rerank_with_openai(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items or not get_openai_api_key():
        return items
    if not _bool_env("RAG_ENABLE_RERANK", default=True):
        return items
    try:
        model = os.environ.get("OPENAI_RERANK_MODEL", os.environ.get("OPENAI_MODEL", "gpt-5-mini"))
        candidates = [
            {"id": i["id"], "title": i["title"], "content": str(i["content"])[:400]}
            for i in items
        ]
        prompt = (
            "与えられた query に対して候補文書を関連度順に並べ替えてください。"
            "JSONで {\"ordered_ids\":[id,...]} のみを返してください。"
            f"\nquery={query}\ncandidates={json.dumps(candidates, ensure_ascii=False)}"
        )
        client = get_openai_client()
        resp = client.responses.create(model=model, input=prompt, temperature=0)
        text = getattr(resp, "output_text", "") or ""
        data = json.loads(text)
        ids = [int(x) for x in data.get("ordered_ids", [])]
        pos = {cid: i for i, cid in enumerate(ids)}
        return sorted(items, key=lambda x: pos.get(int(x["id"]), 10_000))
    except Exception:
        return items


def search_chunks(query: str, limit: int = 5, source_types: list[str] | None = None) -> list[dict[str, Any]]:
    prepared = prepare_search_query(query)
    q_text_tokens = tokenize(prepared["expanded_query"])
    q_dense_tokens = tokenize(prepared["final_query"])
    if not q_text_tokens and not q_dense_tokens:
        return []

    q_counter = Counter(q_text_tokens or q_dense_tokens)

    qs = RagChunk.objects.all()
    if source_types:
        qs = qs.filter(source_type__in=source_types)

    text_scored: list[tuple[int, float, RagChunk]] = []
    for chunk in qs[:2000]:
        c_counter = Counter(chunk.tokens or [])
        inter = sum(min(v, c_counter.get(k, 0)) for k, v in q_counter.items())
        if inter <= 0:
            continue
        score = float(inter) / max(1, len(set(chunk.tokens or [])))
        text_scored.append((chunk.id, score, chunk))

    if not text_scored:
        return []

    text_rank = _rank_map([(cid, s) for cid, s, _ in text_scored])

    dense_rank: dict[int, int] = {}
    dense_enabled = _bool_env("RAG_ENABLE_DENSE_HYBRID", default=True) and bool(get_openai_api_key())
    if dense_enabled:
        candidate_limit = max(limit, _int_env("RAG_HYBRID_CANDIDATES", 80))
        top_text_candidates = sorted(text_scored, key=lambda x: x[1], reverse=True)[:candidate_limit]
        dense_query_text = prepared["final_query"]
        dense_inputs = [dense_query_text] + [str(c.content)[:1200] for _, _, c in top_text_candidates]
        vecs = _embed_texts(dense_inputs)
        if vecs and len(vecs) == len(dense_inputs):
            qv = vecs[0]
            dense_scores: list[tuple[int, float]] = []
            for idx, (cid, _, _) in enumerate(top_text_candidates, start=1):
                dense_scores.append((cid, _cosine_similarity(qv, vecs[idx])))
            dense_rank = _rank_map(dense_scores)

    text_weight = _float_env("RAG_RRF_TEXT_WEIGHT", 1.0)
    dense_weight = _float_env("RAG_RRF_EMBED_WEIGHT", 1.0 if dense_rank else 0.0)
    combined = _apply_rrf(text_rank, dense_rank, text_weight, dense_weight)

    chunks_by_id = {c.id: c for _, _, c in text_scored}
    ranked_ids = [cid for cid, _ in sorted(combined.items(), key=lambda x: x[1], reverse=True)]
    items = [
        {
            "id": cid,
            "score": round(float(combined[cid]), 4),
            "title": chunks_by_id[cid].title,
            "source_type": chunks_by_id[cid].source_type,
            "source_id": chunks_by_id[cid].source_id,
            "content": chunks_by_id[cid].content,
            "metadata": {
                **(chunks_by_id[cid].metadata or {}),
                "retrieval": {
                    "rewrite_query": prepared["rewritten_query"],
                    "hyde_used": bool(prepared["hyde_text"]),
                },
            },
        }
        for cid in ranked_ids
    ]

    rerank_n = _int_env("RAG_RERANK_TOP_N", 20)
    if rerank_n > 1:
        head = _rerank_with_openai(query, items[:rerank_n])
        items = head + items[rerank_n:]

    out = items[:limit]
    return out


def collect_aidocs_documents(base_dir: str | None = None) -> list[dict[str, Any]]:
    root = Path(base_dir or "").expanduser() if base_dir else None
    if root is None or not root.exists():
        return []
    docs: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = str(path.relative_to(root))
        docs.append(
            {
                "title": path.stem,
                "source_id": rel,
                "content": content,
                "metadata": {"path": rel},
            }
        )
    return docs
