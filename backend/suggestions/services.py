from __future__ import annotations

from datasets.models import Dataset, SemanticLabel
from suggestions.models import Suggestion, SuggestionPriority, SuggestionSource


def _labels(dataset: Dataset) -> set[str]:
    sheet = dataset.sheets.filter(selected=True).first()
    if not sheet:
        return set()
    values = sheet.column_profiles.values_list("semantic_label", flat=True)
    return {v for v in values if v and v != SemanticLabel.UNKNOWN and v != SemanticLabel.IGNORE}


def _primary_amount_label(labels: set[str]) -> str | None:
    for lab in (SemanticLabel.AMOUNT_JPY, SemanticLabel.AMOUNT, SemanticLabel.UNIT_PRICE):
        if lab in labels:
            return lab
    return None


def generate_suggestions_for_dataset(dataset: Dataset) -> list[Suggestion]:
    labels = _labels(dataset)
    suggestions: list[Suggestion] = []
    amount_lab = _primary_amount_label(labels)

    if SemanticLabel.DATE in labels and amount_lab:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="売上・金額の時系列分析",
                description="日付と金額系の列で月次・週次トレンドを可視化し、増減要因を確認します。",
                priority=SuggestionPriority.HIGH,
                required_columns=[SemanticLabel.DATE, amount_lab],
                source=SuggestionSource.RULE,
            )
        )

    if SemanticLabel.CUSTOMER in labels and amount_lab:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="顧客別売上ランキング",
                description="顧客ごとの金額合計を比較し、重点フォロー対象を抽出します。",
                priority=SuggestionPriority.MEDIUM,
                required_columns=[SemanticLabel.CUSTOMER, amount_lab],
                source=SuggestionSource.RULE,
            )
        )

    if SemanticLabel.PREFECTURE in labels and amount_lab:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="地域別売上の比較",
                description="都道府県と金額を掛け合わせ、地域集中度と未開拓エリアを把握します。",
                priority=SuggestionPriority.MEDIUM,
                required_columns=[SemanticLabel.PREFECTURE, amount_lab],
                source=SuggestionSource.RULE,
            )
        )

    if SemanticLabel.CATEGORY in labels and amount_lab:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="カテゴリ別の比較",
                description="カテゴリ（例: 商品カテゴリ/科目など）ごとに金額/点数の合計・平均などを比較し、偏りを把握します。",
                priority=SuggestionPriority.MEDIUM,
                required_columns=[SemanticLabel.CATEGORY, amount_lab],
                source=SuggestionSource.RULE,
            )
        )

    if {SemanticLabel.PERSON_NAME, SemanticLabel.AMOUNT_JPY}.issubset(labels) or (
        SemanticLabel.PERSON_NAME in labels and SemanticLabel.AMOUNT in labels
    ):
        plab = SemanticLabel.AMOUNT_JPY if SemanticLabel.AMOUNT_JPY in labels else SemanticLabel.AMOUNT
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="担当者別パフォーマンス",
                description="営業担当者名と売上金額から、担当者ごとの集計比較が可能です。",
                priority=SuggestionPriority.MEDIUM,
                required_columns=[SemanticLabel.PERSON_NAME, plab],
                source=SuggestionSource.RULE,
            )
        )

    if SemanticLabel.QUANTITY in labels and amount_lab:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="数量と金額の関係",
                description="販売数量と単価・売上の関係を確認し、単価帯のばらつきを把握します。",
                priority=SuggestionPriority.LOW,
                required_columns=[SemanticLabel.QUANTITY, amount_lab],
                source=SuggestionSource.RULE,
            )
        )

    if SemanticLabel.STATUS in labels:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="ステータス分布の把握",
                description="案件/チケットのステータス比率を集計し、停滞ポイントを特定します。",
                priority=SuggestionPriority.MEDIUM,
                required_columns=[SemanticLabel.STATUS],
                source=SuggestionSource.RULE,
            )
        )

    if not suggestions:
        suggestions.append(
            Suggestion(
                dataset=dataset,
                title="基本サマリー分析",
                description="主要列の分布・欠損・代表値を確認して分析可能性を整理します。",
                priority=SuggestionPriority.LOW,
                required_columns=[],
                source=SuggestionSource.RULE,
            )
        )

    dataset.suggestions.all().delete()
    created = Suggestion.objects.bulk_create(suggestions)
    return list(created)
