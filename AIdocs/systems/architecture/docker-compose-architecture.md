# Docker Compose Architecture

## compose ファイルの役割

### compose.yml
共通定義。  
サービス定義、ネットワーク、ボリューム、基本環境変数を持つ。

### compose.override.yml
ローカル開発向け。  
bind mount、開発向け command、local settings 等を追加する。

### compose.prod.yml
本番向け。  
Gunicorn 起動、restart policy、prod settings、object storage 用環境変数などを持つ。

## コンテナ一覧

| コンテナ | 役割 |
|---|---|
| nginx | reverse proxy / static 配信 |
| web | Django 本体 / API / admin |
| worker | Django-RQ による非同期処理 |
| db | PostgreSQL |
| redis | キュー / キャッシュ補助 |

## 起動依存
- web は db / redis に依存
- worker は db / redis に依存
- nginx は web に依存

## ボリューム
- db データは永続化
- static volume は web と nginx 間で共有可能
- local では backend bind mount 可
- prod では bind mount しない
