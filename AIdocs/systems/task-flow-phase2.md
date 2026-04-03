# Task Flow Phase 2

## 非同期タスク
1. `profile_dataset`
   - ファイル読込
   - 行数/列数算出
   - 列ごとの profile 作成

2. `infer_semantic_columns`
   - profile を入力に AI 推定
   - semantic_label を保存

## 推奨実行順
upload -> select sheet -> profile -> semantic inference -> review

## チャット分析フロー（追加）
1. `POST /api/chat/ask` で質問受付
2. `run_analysis_job` が dataset を読み込み、実計算（集計）を実行
3. `rag/search` 相当で関連コンテキストを取得
4. OpenAI で説明文を生成（失敗時は deterministic fallback）
5. `GET /api/chat/ask/{id}` で status / answer / evidence / next_actions を取得
