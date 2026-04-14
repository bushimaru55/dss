from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from datasets.models import SemanticLabel

logger = logging.getLogger(__name__)


def _semantic_openai_fallback_enabled() -> bool:
    return os.environ.get("SEMANTIC_OPENAI_FALLBACK", "").strip().lower() in ("1", "true", "yes")


_SEMANTIC_LABEL_VALUES = [c.value for c in SemanticLabel]


def _openai_infer_semantic_label(column_name: str, inferred_type: str, sample_values: list[Any]) -> str:
    from ai.client import get_openai_api_key, get_openai_client

    if not get_openai_api_key():
        return SemanticLabel.UNKNOWN
    samples = sample_values[:8]
    sample_str = json.dumps([str(v) for v in samples], ensure_ascii=False)[:800]
    allowed = ", ".join(_SEMANTIC_LABEL_VALUES)
    prompt = (
        "あなたは表の列の意味を分類します。次の列について、許容値のいずれかひとつだけを JSON で返してください。\n"
        f'形式: {{"semantic_label": "<値>"}}\n'
        f"許容値（そのまま）: {allowed}\n"
        "意味が全く判断できない場合のみ semantic_label に unknown を使ってください。\n"
        "列が明らかに分析対象外（空欄のみ・連番IDのみで意味がない等）なら ignore も可。\n"
        f"列名: {column_name}\n"
        f"推定型: {inferred_type}\n"
        f"サンプル値（JSON）: {sample_str}\n"
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    client = get_openai_client()
    resp = client.responses.create(model=model, input=prompt, temperature=0)
    text = getattr(resp, "output_text", "") or ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return SemanticLabel.UNKNOWN
    raw = data.get("semantic_label")
    if raw is None:
        return SemanticLabel.UNKNOWN
    val = str(raw).strip().lower()
    if val in _SEMANTIC_LABEL_VALUES:
        return val
    return SemanticLabel.UNKNOWN


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
    (r"(商品カテゴリ|品目カテゴリ|カテゴリ|分類|category)", SemanticLabel.CATEGORY),
    (r"(商品名|品名|product[_\s]?name)", SemanticLabel.PRODUCT_NAME),
    (r"(商品コード|sku|品番)", SemanticLabel.PRODUCT),
    (r"(備考|メモ|注記|memo|note)", SemanticLabel.MEMO),
    (r"(会社名|企業名|法人名|company)", SemanticLabel.COMPANY_NAME),
    (r"(状態|ステータス|配送状況|status|state)", SemanticLabel.STATUS),
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
    if _semantic_openai_fallback_enabled():
        try:
            return _openai_infer_semantic_label(key, inferred_type, sample_values)
        except Exception:
            logger.exception("OpenAI semantic fallback failed for column=%r", column_name)
            return SemanticLabel.UNKNOWN
    return SemanticLabel.UNKNOWN
