from rag.query_expansion import expand_query_for_search, prepare_search_query, should_use_hyde


def test_expand_adds_aliases_when_keyword_present():
    out = expand_query_for_search("営業のランキング")
    assert "セールス" in out
    assert "sales" in out
    assert "営業のランキング" in out


def test_expand_empty():
    assert expand_query_for_search("") == ""


def test_prepare_search_query_without_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = prepare_search_query("営業のランキング")
    assert out["original_query"] == "営業のランキング"
    assert "セールス" in out["expanded_query"]
    assert out["rewritten_query"] == out["expanded_query"]
    assert out["hyde_text"] == ""


def test_should_use_hyde_by_short_tokens(monkeypatch):
    monkeypatch.setenv("RAG_ENABLE_HYDE", "true")
    monkeypatch.setenv("RAG_HYDE_MAX_TOKENS", "4")
    assert should_use_hyde("売上トップは?")
    assert not should_use_hyde("営業担当者ごとの売上ランキングと前月比を教えてください")
