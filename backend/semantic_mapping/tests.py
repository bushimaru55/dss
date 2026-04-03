"""DB 不要のルールベース semantic 推論テスト。"""

from datasets.models import SemanticLabel
from semantic_mapping.services import infer_semantic_label


def test_sales_sample_headers():
    cases = [
        ("担当者ID", SemanticLabel.ASSIGNEE),
        ("営業担当者名", SemanticLabel.PERSON_NAME),
        ("所属部門", SemanticLabel.DEPARTMENT),
        ("販売日", SemanticLabel.DATE),
        ("顧客名", SemanticLabel.CUSTOMER),
        ("都道府県", SemanticLabel.PREFECTURE),
        ("商品カテゴリ", SemanticLabel.CATEGORY),
        ("商品名", SemanticLabel.PRODUCT_NAME),
        ("販売数量", SemanticLabel.QUANTITY),
        ("単価(円)", SemanticLabel.UNIT_PRICE),
        ("売上金額(円)", SemanticLabel.AMOUNT_JPY),
        ("備考", SemanticLabel.MEMO),
    ]
    for name, expected in cases:
        got = infer_semantic_label(name, "string", [])
        assert got == expected, f"{name!r} -> {got} expected {expected}"


def test_amount_jpy_from_yen_in_name_when_number():
    assert infer_semantic_label("売上_円計", "number", []) == SemanticLabel.AMOUNT_JPY
