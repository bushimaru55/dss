from __future__ import annotations

from django.core.management.base import BaseCommand

from rag.eval import SynonymEvalCase, evaluate_synonym_cases


class Command(BaseCommand):
    help = "RAG 同義語検索の簡易評価（recall/latency）"

    def handle(self, *args, **options):
        cases = [
            SynonymEvalCase(query="営業担当者の売上トップ", expected_any=["営業", "担当者", "売上"]),
            SynonymEvalCase(query="セールスのランキング", expected_any=["営業", "売上", "ランキング"]),
            SynonymEvalCase(query="取引先ごとの売上", expected_any=["顧客", "取引先", "売上"]),
            SynonymEvalCase(query="顧客別の上位", expected_any=["顧客", "上位", "ランキング"]),
        ]
        out = evaluate_synonym_cases(cases, limit=5)
        self.stdout.write(self.style.SUCCESS("rag synonym eval"))
        self.stdout.write(f"total={out['total']}")
        self.stdout.write(f"hits={out['hits']}")
        self.stdout.write(f"recall_at_k={out['recall_at_k']:.3f}")
        self.stdout.write(f"latency_p95_ms={out['latency_p95_ms']}")
        self.stdout.write(f"elapsed_ms={out['elapsed_ms']}")
        for d in out["details"]:
            self.stdout.write(
                f"- query={d['query']} hit={d['hit']} latency_ms={d['latency_ms']} top_titles={','.join(d['top_titles'])}"
            )
