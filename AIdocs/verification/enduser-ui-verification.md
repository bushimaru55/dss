# Verification: Enduser UI

## 実施日
2026-03-27

## 確認項目
- `/app/login` でログインできる
- `/app/datasets/new` で upload できる
- アップロード後 `/app/datasets/{id}/import` に遷移し、プレビュー（解釈済み／生データ）・ヘッダー行・レコード同意チェック後に「この解釈で進む」で詳細へ進める
- dataset 詳細で分析準備を実行できる（インポート確認で未実行の場合）
- suggestions 候補が画面表示される

## 結果
- 成功（local）
- `/app/login` でログイン画面表示を確認（HTTP 200）
- `/app/` で dataset 一覧表示を確認
- `/app/datasets/{id}/import` でプレビューと確定後、`/app/datasets/{id}` で候補表示を確認
- 自動テスト: `docker compose exec -T web pytest -q` -> `8 passed`
