from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from rag.services import search_chunks


@dataclass(frozen=True)
class SynonymEvalCase:
    query: str
    expected_any: list[str]


def evaluate_synonym_cases(cases: list[SynonymEvalCase], limit: int = 5) -> dict[str, Any]:
    start_all = time.perf_counter()
    details: list[dict[str, Any]] = []
    hit_count = 0
    latencies_ms: list[float] = []

    for c in cases:
        t0 = time.perf_counter()
        items = search_chunks(c.query, limit=limit, source_types=["manual", "aidocs"])
        elapsed = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed)
        hit = any(any(k in (it.get("content") or "") for k in c.expected_any) for it in items)
        if hit:
            hit_count += 1
        details.append(
            {
                "query": c.query,
                "hit": hit,
                "top_titles": [str(x.get("title", "")) for x in items[:3]],
                "latency_ms": round(elapsed, 2),
            }
        )

    total = len(cases)
    p95 = sorted(latencies_ms)[max(0, int(total * 0.95) - 1)] if latencies_ms else 0.0
    return {
        "total": total,
        "hits": hit_count,
        "recall_at_k": (hit_count / total) if total else 0.0,
        "latency_p95_ms": round(float(p95), 2),
        "elapsed_ms": round((time.perf_counter() - start_all) * 1000, 2),
        "details": details,
    }
