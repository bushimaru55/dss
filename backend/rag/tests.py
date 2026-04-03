from django.urls import reverse


def test_rag_index_and_search(auth_client):
    index_res = auth_client.post(
        "/api/rag/index",
        data={
            "source_type": "manual",
            "replace_scope": "seed1",
            "documents": [
                {
                    "title": "売上定義",
                    "source_id": "seed1",
                    "content": "売上金額は税込金額を使います。ステータスopenは未完了を意味します。",
                    "metadata": {"domain": "sales"},
                }
            ],
        },
        format="json",
    )
    assert index_res.status_code == 200
    assert index_res.data["count"] >= 1

    search_res = auth_client.post(
        "/api/rag/search",
        data={"query": "売上金額の定義", "limit": 3},
        format="json",
    )
    assert search_res.status_code == 200
    assert len(search_res.data["items"]) >= 1
    first = search_res.data["items"][0]
    assert "retrieval" in first["metadata"]
    assert "rewrite_query" in first["metadata"]["retrieval"]
