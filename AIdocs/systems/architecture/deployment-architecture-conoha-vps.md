# Deployment Architecture on ConoHa VPS

## 配置イメージ
ConoHa VPS 1台上で Docker Compose を利用して各コンテナを起動する。

```text
Browser
  ↓
nginx:80/443
  ↓
web:8000 (gunicorn)
  ├─ PostgreSQL:5432
  ├─ Redis:6379
  └─ ConoHa Object Storage (external)
```

## 使用ポート
- nginx: 80 / 443
- web: 内部 8000
- db: 内部 5432
- redis: 内部 6379

## 永続化対象
- PostgreSQL data
- 必要な .env / secrets
- deployment 設定ファイル

## バックアップ対象
- DB データ
- 環境変数管理情報
- Object Storage 側のデータ
- AIdocs / ソースコード
