# Runbook: Preprocessing Foundation (Local)

## 前提
- `docker compose up -d` 済み
- admin user 作成済み
- token 取得可能

## 手順
1. CSV または XLSX を upload
2. `GET /sheets/` でシート一覧確認（Excel のみ複数）
3. `GET /preview/` でヘッダ候補・警告を確認
4. `POST /profile/` で profiling 実行
5. `GET /profile/` で列プロファイル確認
6. `POST /semantic-mapping/generate/` で候補生成
7. `POST /semantic-mapping/` で user 修正保存

## チェック観点
- Unnamed 列が補正候補として見えるか
- 結合セル検知、2段ヘッダ警告が出るか
- null/unique/sample/type が列ごとに返るか
- semantic source が `ai -> user` に更新されるか

## 失敗時
- `docker compose logs -f web`
- `docker compose logs -f worker`
- `GET /api/datasets/{id}/` の `error_message` を確認
