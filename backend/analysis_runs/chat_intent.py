"""チャット質問の軽量意図検出（ルールベース）。類義語・表記ゆれに対応するためのキーワード分類。"""

from __future__ import annotations

import re
from typing import Literal

QueryIntent = Literal["person_ranking", "customer_ranking", "general"]

# 担当者・営業系（英字は単語境界を考慮）
_PERSON_PAT = re.compile(
    r"(担当者|営業担当|営業マン|営業員|セールス|営業(?!部|課)|sales\s*rep|salesrep|\brep\b|生徒|学生|受講者|児童)",
    re.IGNORECASE,
)
_CUSTOMER_PAT = re.compile(r"(顧客|取引先|クライアント|得意先|お客様)")


def detect_ranking_intent(question: str) -> QueryIntent:
    """
    ランキング系の質問で「誰を軸に並べるか」のヒント。
    - person_ranking: 営業・担当者など
    - customer_ranking: 顧客・取引先など（明示時）
    - general: 合計のみ・期間・その他
    """
    q = question or ""
    has_person = bool(_PERSON_PAT.search(q))
    has_customer = bool(_CUSTOMER_PAT.search(q))

    if has_customer and not has_person:
        return "customer_ranking"
    if has_person:
        return "person_ranking"
    if has_customer:
        return "customer_ranking"
    return "general"


def build_semantic_column_hints(labels: dict[str, str]) -> dict[str, str]:
    """semantic_label -> 実際の列名（最初の1列）。"""
    out: dict[str, str] = {}
    for col_name, lab in labels.items():
        if lab not in out:
            out[lab] = col_name
    return out
