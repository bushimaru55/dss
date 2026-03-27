# Runbook: Initial Setup (ConoHa VPS)

## 前提
- Ubuntu 24.04 系
- sudo 権限あり
- Docker / Docker Compose をインストール済み

## 手順
1. リポジトリを配置する
2. `.env` を本番用に作成する
3. `compose.yml` と `compose.prod.yml` を使って起動する
```bash
docker compose -f compose.yml -f compose.prod.yml up --build -d
```

4. migrate
```bash
docker compose -f compose.yml -f compose.prod.yml exec web python manage.py migrate
```

5. collectstatic
```bash
docker compose -f compose.yml -f compose.prod.yml exec web python manage.py collectstatic --noinput
```

6. superuser 作成
```bash
docker compose -f compose.yml -f compose.prod.yml exec web python manage.py createsuperuser
```

## 起動確認
```bash
docker compose -f compose.yml -f compose.prod.yml ps
curl -i http://127.0.0.1/health/
```

## 追加確認
- nginx が応答するか
- Gunicorn が web 内で起動しているか
- worker が起動しているか
