# Runbook: Worker Operations

## worker 起動確認
```bash
docker compose ps
docker compose logs -f worker
```

## queue 情報確認
```bash
docker compose exec web python manage.py rqstats
```

## worker コンテナでコマンド実行
```bash
docker compose exec worker bash
```

## タスク投入確認
- Django shell から簡易ジョブを enqueue する
- worker log に実行痕跡が出ることを確認する

## 失敗時の確認
- Redis URL
- worker command
- Django settings module
- import error
