# Runbook: Enduser UI (Local)

## 前提
- `docker compose up -d` 済み
- `admin/admin` などのログイン可能ユーザーが存在

## 手順
1. `http://localhost:8080/app/login` を開く
2. エンドユーザーでログイン
3. `新規アップロード` から CSV/XLSX を登録
4. Dataset 詳細画面で `分析準備を実行` を押す
5. `分析候補` セクションに候補が表示されることを確認

## 確認ポイント
- 管理画面 (`/admin/`) と UI 導線が分離されている
- upload 後に dataset 詳細へ遷移する
- profile/semantic/suggestions が生成される
- 候補タイトルと説明が表示される
