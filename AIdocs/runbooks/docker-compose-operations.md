# Runbook: Docker Compose Operations

## 起動
```bash
docker compose up -d
```

## build 付き起動
```bash
docker compose up --build -d
```

## 停止
```bash
docker compose down
```

## 再起動
```bash
docker compose restart
```

## logs 確認
```bash
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f nginx
docker compose logs -f db
docker compose logs -f redis
```

## コンテナに入る
```bash
docker compose exec web bash
docker compose exec db bash
```

## image rebuild
```bash
docker compose build --no-cache
```
