# API Design Phase 2

## Endpoints

### POST /api/datasets/
ファイルアップロードを受け付ける。

### GET /api/datasets/{id}/
Dataset 詳細取得。

### GET /api/datasets/{id}/sheets/
Excel シート一覧取得（CSV は1件）。

### GET /api/datasets/{id}/preview/?sheet_id=&rows=&header_row=&mode=
選択シートのプレビュー取得。`header_row` に 1 始まりの行番号を指定するとその行をヘッダーとして解釈する（省略時は自動検出）。`mode=interpreted`（既定）で列名付きの解釈済みプレビュー（`DatasetPreview` を保存し `status` が `previewed` になる）。`mode=raw` では `header=None` で読んだ生グリッドを返し、DB には保存しない。

### POST /api/datasets/{id}/import-settings/
インポート確認用。JSON で `sheet_id`（必須）、`header_row`（省略または null で自動）、`record_grain_ack`（任意）を渡し、シート選択・ヘッダー行上書き・`structure_status=confirmed`・`analysis.record_grain_ack` を保存する。続けて `POST .../profile/` でプロファイルを実行する想定。

### POST /api/datasets/{id}/select-sheet/
対象シート選択。

### POST /api/datasets/{id}/profile/
profile 生成ジョブ投入。

### GET /api/datasets/{id}/profile/
profile 結果取得。

### POST /api/datasets/{id}/semantic-mapping/
semantic label の保存。

### POST /api/datasets/{id}/semantic-mapping/generate/
semantic 候補の再生成（ルールベース）。

### GET /api/datasets/{id}/semantic-mapping/
semantic mapping 一覧取得。

### POST /api/chat/ask
質問を受け取り analysis run を非同期実行する（202）。

### GET /api/chat/ask/{analysis_run_id}
analysis run の状態・回答・根拠・次アクションを取得する。

#### チャット集計・類義語まわり（実装概要）

- **metrics**: `amount_sum` / `amount_avg`、`top_customers`（顧客列×金額）、`top_by_person`（担当者名など person 系×金額）、任意で `status_distribution`。
- **query_intent**: 質問文のルールベース分類（`person_ranking` / `customer_ranking` / `general`）。「営業」「担当者」「セールス」等は担当者軸、「顧客」「取引先」等は顧客軸を優先してフォールバック回答を組み立てる。
- **semantic_column_hints**: semantic ラベルから実列名への対応を LLM プロンプトに渡し、metrics に無い推測を禁止する。
- **RAG クエリ前処理**: `backend/rag/query_expansion.py` の `prepare_search_query` で `expand_query_for_search`（固定同義語）→ `rewrite_query_with_openai`（任意: OpenAIクエリ最適化）→ `generate_hypothetical_query_passage`（任意HyDE）を段階適用する。
- **Hybrid retrieval**: `backend/rag/services.py` の `search_chunks` は textスコア（トークン重複）と denseスコア（OpenAI Embeddings）を併用し、RRFで統合する。
- **Re-ranking**: 上位N件（`RAG_RERANK_TOP_N`）をOpenAIで再並び替えし、根拠候補の順序精度を上げる。
- **評価コマンド**: `python manage.py eval_rag_synonyms` で同義語クエリの recall/latency を簡易計測する。
- **主な環境変数**: `RAG_ENABLE_QUERY_REWRITE`, `RAG_ENABLE_DENSE_HYBRID`, `RAG_ENABLE_RERANK`, `RAG_ENABLE_HYDE`, `RAG_RRF_TEXT_WEIGHT`, `RAG_RRF_EMBED_WEIGHT`。

### POST /api/rag/index
RAG 用ドキュメントを chunk 化して index する。

### POST /api/rag/search
質問文に対して関連 chunk を検索して返す。
