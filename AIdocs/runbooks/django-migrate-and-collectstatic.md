# Runbook: Django Migrate and Collectstatic

## migrate
```bash
docker compose exec web python manage.py migrate
```

## collectstatic
```bash
docker compose exec web python manage.py collectstatic --noinput
```

## 本番
```bash
docker compose -f compose.yml -f compose.prod.yml exec web python manage.py migrate
docker compose -f compose.yml -f compose.prod.yml exec web python manage.py collectstatic --noinput
```

## 失敗時の確認ポイント
- DB 接続情報が正しいか
- `ALLOWED_HOSTS` ではなく DB 環境変数の問題ではないか
- static volume / path 設定が正しいか
- 権限エラーがないか
