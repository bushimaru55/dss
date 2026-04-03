"""意図検出の単体テスト（DB 不要）。"""

from analysis_runs.chat_intent import build_semantic_column_hints, detect_ranking_intent
from datasets.models import SemanticLabel


def test_detect_person_intent_variants():
    assert detect_ranking_intent("売上が一位の営業担当者名を教えて") == "person_ranking"
    assert detect_ranking_intent("セールスでトップは誰") == "person_ranking"
    assert detect_ranking_intent("担当者別の売上ランキング") == "person_ranking"


def test_detect_customer_intent():
    assert detect_ranking_intent("顧客別の売上トップは") == "customer_ranking"
    assert detect_ranking_intent("取引先ごとの合計") == "customer_ranking"


def test_detect_general():
    assert detect_ranking_intent("売上の合計だけ教えて") == "general"
    assert detect_ranking_intent("") == "general"


def test_semantic_hints_first_column_per_label():
    labels = {
        "売上金額(円)": SemanticLabel.AMOUNT_JPY,
        "備考": SemanticLabel.MEMO,
    }
    h = build_semantic_column_hints(labels)
    assert h[SemanticLabel.AMOUNT_JPY] == "売上金額(円)"
    assert h[SemanticLabel.MEMO] == "備考"
