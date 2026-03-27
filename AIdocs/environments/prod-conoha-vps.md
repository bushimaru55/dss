# Production Environment on ConoHa VPS

## 概要
本番環境は ConoHa VPS 上で Docker Compose を用いて運用する。  
Django は Gunicorn で起動し、nginx が reverse proxy と static 配信を担う。

## 本番コンテナ構成
- nginx
- web (Django + Gunicorn)
- worker (Django-RQ worker)
- db (PostgreSQL)
- redis

## 外部公開の流れ
```text
Internet -> nginx -> gunicorn(web) -> Django
                         ├-> PostgreSQL
                         ├-> Redis
                         └-> ConoHa Object Storage
```

## ストレージ方針
- static: `collectstatic` 後に nginx 配信
- media / uploads / reports: Object Storage を利用
- `USE_S3=true` の場合に object storage backend を有効化

## settings
- `config.settings.prod`

## compose
- `compose.yml`
- `compose.prod.yml`

## 本番運用の要点
- `DEBUG=False`
- `ALLOWED_HOSTS` を明示
- `CSRF_TRUSTED_ORIGINS` を明示
- secure cookie を有効化
- Gunicorn を利用
- 永続化対象は DB ボリュームと必要な設定ファイル
