from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from ai.client import get_openai_client
from analysis_runs.audit_log import append_audit_record_for_run
from analysis_runs.chat_intent import build_semantic_column_hints, detect_ranking_intent
from analysis_runs.models import AnalysisRun
from datasets.models import Dataset, SemanticLabel, SheetStructureStatus
from profiling.services import PandasTabularReader
from rag.services import search_chunks

# 分析ファクト層（result_json 正本）のスキーマ版。AIdocs changes/2026-04-14-analysis-facts-layer-prototype-plan.md 参照。
ANALYSIS_FACTS_SCHEMA_VERSION = {"analysis_facts": 1}


def _selected_sheet(dataset: Dataset):
    return dataset.sheets.filter(selected=True).first()


def _semantic_map(dataset: Dataset) -> dict[str, str]:
    sheet = _selected_sheet(dataset)
    if not sheet:
        return {}
    return {r.column_name: r.semantic_label for r in sheet.column_profiles.all()}


def _pick_column(labels: dict[str, str], wanted: set[str]) -> str | None:
    for name, label in labels.items():
        if label in wanted:
            return name
    return None


def _pick_column_priority(labels: dict[str, str], priority: list[str]) -> str | None:
    for lab in priority:
        for name, l in labels.items():
            if l == lab:
                return name
    return None


def _amount_numeric_series(df: pd.DataFrame, amount_col: str) -> pd.Series:
    s = (
        df[amount_col]
        .astype(str)
        .str.replace("¥", "", regex=False)
        .str.replace("円", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    return s.replace({"": None, "nan": None}).astype(float)


def _top_by_dimension(
    df: pd.DataFrame,
    dim_col: str,
    amount_col: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    tmp = df[[dim_col, amount_col]].copy()
    tmp[amount_col] = _amount_numeric_series(tmp, amount_col)
    grp = tmp.groupby(dim_col, dropna=True)[amount_col].sum().sort_values(ascending=False)
    return [{"name": str(idx), "amount": float(val)} for idx, val in grp.head(limit).items()]


def run_analysis_to_completion(run_id: int) -> None:
    """RQ ジョブと同期 UI の双方から呼ぶ。失敗時は AnalysisRun を FAILED に更新する。"""
    run = AnalysisRun.objects.select_related("dataset").get(pk=run_id)
    run.status = AnalysisRun.Status.RUNNING
    run.error_message = ""
    run.save(update_fields=["status", "error_message", "updated_at"])

    try:
        out = execute_analysis(run.dataset, run.question)
        run.plan_json = out.get("plan", {})
        facts = out.get("facts") or {}
        run.result_json = facts
        run.answer = out.get("answer", "")
        fact_keys = list(facts.keys())
        run.evidence = {
            "fact_keys": fact_keys,
            "metrics_keys": fact_keys,
            "rag_items": out.get("rag_items", []),
        }
        run.confidence = float(out.get("confidence", 0.0))
        run.next_actions = out.get("next_actions", [])
        run.status = AnalysisRun.Status.SUCCEEDED
        run.save(
            update_fields=[
                "plan_json",
                "result_json",
                "answer",
                "evidence",
                "confidence",
                "next_actions",
                "status",
                "updated_at",
            ]
        )
    except Exception as exc:
        run.status = AnalysisRun.Status.FAILED
        run.error_message = str(exc)
        run.save(update_fields=["status", "error_message", "updated_at"])
    finally:
        run.refresh_from_db()
        append_audit_record_for_run(run)


def execute_analysis(dataset: Dataset, question: str) -> dict[str, Any]:
    sheet = _selected_sheet(dataset)
    if not sheet:
        raise RuntimeError("No selected sheet")
    if sheet.structure_status == SheetStructureStatus.NEEDS_REVIEW:
        raise RuntimeError(
            "表の行・列の構造が未確認です。エンドユーザー画面または管理画面でヘッダー行を確定してください。"
        )

    reader = PandasTabularReader()
    path = Path(dataset.file.path)
    sheet_name = None if dataset.file_type == "csv" else sheet.name
    hr = sheet.header_row_override
    df = reader.read_dataframe(path, dataset.file_type, sheet_name, header_row_1based=hr)

    labels = _semantic_map(dataset)
    amount_col = _pick_column_priority(
        labels,
        [SemanticLabel.AMOUNT_JPY, SemanticLabel.AMOUNT, SemanticLabel.UNIT_PRICE],
    )
    date_col = _pick_column_priority(labels, [SemanticLabel.DATE, SemanticLabel.DATETIME])
    customer_col = _pick_column_priority(
        labels,
        [SemanticLabel.CUSTOMER, SemanticLabel.COMPANY_NAME],
    )
    person_col = _pick_column_priority(labels, [SemanticLabel.PERSON_NAME, SemanticLabel.ASSIGNEE])
    status_col = _pick_column(labels, {SemanticLabel.STATUS})

    query_intent = detect_ranking_intent(question)

    facts: dict[str, Any] = {
        "schema_version": dict(ANALYSIS_FACTS_SCHEMA_VERSION),
        "row_count": int(len(df)),
        "columns": list(map(str, df.columns)),
        "query_intent": query_intent,
        "semantic_column_hints": build_semantic_column_hints(labels),
        "detected_columns": {
            "amount": amount_col,
            "date": date_col,
            "customer": customer_col,
            "person": person_col,
            "status": status_col,
        },
    }

    if amount_col and amount_col in df.columns:
        amount_num = _amount_numeric_series(df, amount_col)
        facts["amount_sum"] = float(amount_num.sum(skipna=True))
        facts["amount_avg"] = float(amount_num.mean(skipna=True)) if amount_num.notna().any() else 0.0

    if customer_col and amount_col and customer_col in df.columns and amount_col in df.columns:
        facts["top_customers"] = _top_by_dimension(df, customer_col, amount_col, limit=5)

    if person_col and amount_col and person_col in df.columns and amount_col in df.columns:
        facts["top_by_person"] = _top_by_dimension(df, person_col, amount_col, limit=5)

    if status_col and status_col in df.columns:
        cnt = df[status_col].fillna("(null)").astype(str).value_counts().head(10)
        facts["status_distribution"] = [
            {"status": str(idx), "count": int(val)} for idx, val in cnt.items()
        ]

    plan = {
        "strategy": "deterministic_dataframe_aggregation",
        "question": question,
        "query_intent": query_intent,
        "used_columns": facts["detected_columns"],
    }

    rag_items = search_chunks(question, limit=4, source_types=["manual", "aidocs"])
    answer = _compose_answer_with_llm_or_fallback(question, facts, rag_items)
    return {
        "plan": plan,
        "facts": facts,
        "rag_items": rag_items,
        **answer,
    }


def _compose_answer_with_llm_or_fallback(
    question: str, facts: dict[str, Any], rag_items: list[dict[str, Any]]
) -> dict[str, Any]:
    if not os.environ.get("OPENAI_API_KEY"):
        return _fallback_answer(question, facts, rag_items)

    try:
        client = get_openai_client()
        model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        hints = facts.get("semantic_column_hints") or {}
        intent = facts.get("query_intent") or "general"
        prompt = (
            "あなたはデータ分析アシスタントです。\n"
            "次のルールを厳守してください。\n"
            "1) 回答は analysis_facts と rag_context に明示された数値・ランキングのみを根拠にすること。"
            "2) analysis_facts にない集計・推測・補完は行わないこと。"
            "3) semantic_column_hints は各 semantic ラベルに対応する実列名のヒントです。"
            "質問が「営業」「担当者」「顧客」など別の言い回しでも、"
            "query_intent と top_by_person / top_customers の有無に従って解釈すること。\n"
            f"query_intent={intent}\n"
            f"semantic_column_hints={json.dumps(hints, ensure_ascii=False)}\n"
            "JSONで返してください。キーは answer, confidence, next_actions。"
            f"\nquestion={question}\nanalysis_facts={json.dumps(facts, ensure_ascii=False)}\nrag_context={json.dumps(rag_items, ensure_ascii=False)}"
        )
        resp = client.responses.create(
            model=model,
            input=prompt,
            temperature=0,
        )
        text = getattr(resp, "output_text", "") or ""
        data = json.loads(text)
        ans = str(data.get("answer", ""))
        conf = float(data.get("confidence", 0.6))
        next_actions = data.get("next_actions", [])
        if not isinstance(next_actions, list):
            next_actions = [str(next_actions)]
        return {
            "answer": ans,
            "confidence": max(0.0, min(1.0, conf)),
            "next_actions": [str(x) for x in next_actions][:5],
        }
    except Exception:
        return _fallback_answer(question, facts, rag_items)


def _fallback_answer(question: str, facts: dict[str, Any], rag_items: list[dict[str, Any]]) -> dict[str, Any]:
    parts = [f"質問: {question}"]
    intent = facts.get("query_intent") or "general"
    top_person = facts.get("top_by_person") or []
    top_cust = facts.get("top_customers") or []

    if "amount_sum" in facts:
        parts.append(f"金額合計は {facts['amount_sum']:.2f} です。")
    if "amount_avg" in facts:
        parts.append(f"金額平均は {facts['amount_avg']:.2f} です。")

    if intent == "person_ranking" and top_person:
        top = top_person[0]
        parts.append(f"担当者別では {top['name']} が売上最大です。")
    elif intent == "customer_ranking" and top_cust:
        top = top_cust[0]
        parts.append(f"顧客別では {top['name']} が最大です。")
    elif top_cust:
        top = top_cust[0]
        parts.append(f"顧客別では {top['name']} が最大です。")
    elif top_person:
        top = top_person[0]
        parts.append(f"担当者別では {top['name']} が売上最大です。")

    if facts.get("status_distribution"):
        s = facts["status_distribution"][0]
        parts.append(f"ステータス最多は {s['status']} ({s['count']}件) です。")
    if len(parts) == 1:
        parts.append("有効な分析列が不足しているため、profile/semantic mapping の見直しを推奨します。")
    if rag_items:
        parts.append(f"参考情報: {rag_items[0]['title']} を参照しました。")
    return {
        "answer": " ".join(parts),
        "confidence": 0.65,
        "next_actions": [
            "必要列のsemantic mappingを確認する",
            "期間条件を指定して再質問する",
        ],
    }
