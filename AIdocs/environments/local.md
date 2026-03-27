# Local Environment

## 概要
ローカル開発は Docker Compose を利用する。  
`compose.yml` と `compose.override.yml` により、開発向け設定で web / worker / db / redis / nginx を起動する。

## 想定構成
- nginx
- web (Django)
- worker (Django-RQ)
- db (PostgreSQL)
- redis

## settings
- `config.settings.local`

## 起動コマンド
```bash
docker compose up --build
```

## 初回セットアップ
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
```

## アクセスURL
- アプリ: `http://localhost:8080/`
- health: `http://localhost:8080/health/`
- admin: `http://localhost:8080/admin/`

## よく使う確認コマンド
```bash
docker compose ps
docker compose logs -f web
docker compose logs -f worker
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py rqstats
```
