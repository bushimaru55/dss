# Environments Overview

## 目的
Data Solution Studio の実行環境を整理し、各環境の役割と参照先を明確にする。

## 環境一覧

| 環境 | 目的 | 主な用途 |
|---|---|---|
| local | 開発・検証 | Docker Compose による日常開発 |
| prod-conoha-vps | 本番運用 | ConoHa VPS 上での実サービス運用 |

## 共通方針
- コンテナ実行を前提とする
- Django を中核にした modular monolith を採用する
- web と worker は分離する
- static は nginx 配信
- media / uploads / reports は Object Storage へ切替可能にする

## 主要サービス
- nginx
- Django web
- Django worker
- PostgreSQL
- Redis
- ConoHa Object Storage（本番想定）

## 参照先
- local: [local.md](local.md)
- prod: [prod-conoha-vps.md](prod-conoha-vps.md)
