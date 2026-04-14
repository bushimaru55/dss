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


def test_unknown_without_openai_fallback(monkeypatch):
    monkeypatch.delenv("SEMANTIC_OPENAI_FALLBACK", raising=False)
    assert infer_semantic_label("社内コード_αβ", "string", ["x", "y"]) == SemanticLabel.UNKNOWN


def test_openai_fallback_when_enabled(monkeypatch):
    monkeypatch.setenv("SEMANTIC_OPENAI_FALLBACK", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    class _Resp:
        output_text = '{"semantic_label": "memo"}'

    class _Responses:
        def create(self, **kwargs):
            return _Resp()

    class _Client:
        def __init__(self):
            self.responses = _Responses()

    monkeypatch.setattr("ai.client.get_openai_client", lambda: _Client())

    got = infer_semantic_label("社内コード_αβ", "string", ["備考欄です"])
    assert got == SemanticLabel.MEMO
