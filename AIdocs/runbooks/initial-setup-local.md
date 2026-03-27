# Runbook: Initial Setup (Local)

## 前提
- Docker / Docker Compose が利用可能
- リポジトリが取得済み

## 手順
1. 環境変数ファイルを作成する
```bash
cp .env.example .env
```

2. コンテナを build / 起動する
```bash
docker compose up --build -d
```

3. migration を実行する
```bash
docker compose exec web python manage.py migrate
```

4. collectstatic を実行する
```bash
docker compose exec web python manage.py collectstatic --noinput
```

5. superuser を作成する
```bash
docker compose exec web python manage.py createsuperuser
```

## 確認
```bash
docker compose ps
curl -i http://localhost:8080/health/
```

## 問題がある場合
- `docker compose logs -f web`
- `docker compose logs -f worker`
- `docker compose logs -f db`
