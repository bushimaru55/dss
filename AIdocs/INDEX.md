# AIdocs INDEX

本ディレクトリは **Data Solution Studio** の Single Source of Truth です。  
設計、環境、運用手順、確認結果、変更履歴はすべて AIdocs に記録します。

## ドキュメント方針
- コード変更だけで終わらせず、関連する設計・runbook・verification を更新する
- 実装前に設計を整理する
- 実装後に確認結果を verification に残す
- 運用手順は runbooks に残す

## 環境
- [環境概要](environments/00_OVERVIEW.md)
- [ローカル環境](environments/local.md)
- [本番環境（ConoHa VPS）](environments/prod-conoha-vps.md)

## システム設計
- [Data Solution Studio 概要](systems/architecture/data-solution-studio-overview.md)
- [Docker Compose 構成](systems/architecture/docker-compose-architecture.md)
- [Django app 構成](systems/architecture/django-app-structure.md)
- [ストレージ戦略](systems/architecture/storage-strategy.md)
- [ConoHa VPS 配置構成](systems/architecture/deployment-architecture-conoha-vps.md)

## Runbooks
- [初期セットアップ（local）](runbooks/initial-setup-local.md)
- [初期セットアップ（ConoHa VPS）](runbooks/initial-setup-conoha-vps.md)
- [Docker Compose 運用](runbooks/docker-compose-operations.md)
- [migrate / collectstatic](runbooks/django-migrate-and-collectstatic.md)
- [worker 運用](runbooks/worker-operations.md)
- [Object Storage 設定](runbooks/object-storage-setup.md)

## Verification
- [初期コンテナ build 結果](verification/initial-container-build-report.md)
- [local 起動確認](verification/local-startup-verification.md)
- [nginx / gunicorn 確認](verification/nginx-gunicorn-verification.md)
- [PostgreSQL / Redis 確認](verification/postgres-redis-verification.md)

## Changes
- [2026-03-27 初期基盤構築](changes/2026-03-27-initial-foundation.md)
