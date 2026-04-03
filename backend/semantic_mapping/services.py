from __future__ import annotations

import re
from typing import Any

from datasets.models import SemanticLabel


# 先に具体的なパターン、後に汎用（最初の一致を採用）
RULES: list[tuple[str, str]] = [
    # education / generic tabular
    (r"(生徒名|学生名|氏名|名前|受講者名|児童名)", SemanticLabel.PERSON_NAME),
    (r"(学籍番号|学生id|生徒id|出席番号)", SemanticLabel.ASSIGNEE),
    (r"(クラス|組|学年|学級)", SemanticLabel.DEPARTMENT),
    (r"(科目|教科|subject)", SemanticLabel.CATEGORY),
    (r"(点数|得点|スコア|score|偏差値|成績)", SemanticLabel.AMOUNT),

    (r"(売上金額|売上額|売上\(円\)|売上（円）)", SemanticLabel.AMOUNT_JPY),
    (r"(単価|unit[_\s]?price)", SemanticLabel.UNIT_PRICE),
    (r"(販売数量|販売数|受注数量|数量|qty|quantity)", SemanticLabel.QUANTITY),
    (r"(担当者id|担当者コード|rep[_\s]?id)", SemanticLabel.ASSIGNEE),
    (r"(営業担当者名|担当者名|氏名|担当者（名）)", SemanticLabel.PERSON_NAME),
    (r"(所属部門|事業部|部門|department|dept)", SemanticLabel.DEPARTMENT),
    (r"(販売日|受注日|購入日|納期|発注日|計上日)", SemanticLabel.DATE),
    (r"(顧客名|顧客|クライアント|取引先名)", SemanticLabel.CUSTOMER),
    (r"(都道府県|prefecture)", SemanticLabel.PREFECTURE),
    (r"(市区町村|city)", SemanticLabel.CITY),
    (r"(商品カテゴリ|品目カテゴリ|カテゴリ|category)", SemanticLabel.CATEGORY),
    (r"(商品名|品名|product[_\s]?name)", SemanticLabel.PRODUCT_NAME),
    (r"(商品コード|sku|品番)", SemanticLabel.PRODUCT),
    (r"(備考|メモ|注記|memo|note)", SemanticLabel.MEMO),
    (r"(会社名|企業名|法人名|company)", SemanticLabel.COMPANY_NAME),
    (r"(状態|ステータス|status|state)", SemanticLabel.STATUS),
    (r"(mail|email|メール)", SemanticLabel.EMAIL),
    (r"(電話|tel|phone|携帯)", SemanticLabel.PHONE),
    (r"(件数|回数|count)", SemanticLabel.COUNT),
    (r"(日時|datetime|timestamp)", SemanticLabel.DATETIME),
    (r"(日付|date)(?!時)", SemanticLabel.DATE),
    (r"(税込|円|jpy)", SemanticLabel.AMOUNT_JPY),
    (r"(売上|金額|amount|price)", SemanticLabel.AMOUNT),
]


def infer_semantic_label(column_name: str, inferred_type: str, sample_values: list[Any]) -> str:
    key = str(column_name)
    for pattern, label in RULES:
        if re.search(pattern, key, flags=re.IGNORECASE):
            return label
    if inferred_type == "date":
        return SemanticLabel.DATE
    if inferred_type == "number":
        if re.search(r"(円|jpy|¥)", key, flags=re.IGNORECASE):
            return SemanticLabel.AMOUNT_JPY
        joined = " ".join(str(v) for v in sample_values[:5]).lower()
        if any(x in joined for x in ("¥", "円", "jpy")):
            return SemanticLabel.AMOUNT_JPY
        return SemanticLabel.AMOUNT
    return SemanticLabel.UNKNOWN
