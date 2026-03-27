# Storage Strategy

## 基本方針
- static は nginx 配信
- media / uploads / generated reports は local と object storage を切替可能にする

## local
- `FileSystemStorage` を利用
- `backend/media/` に保存

## production
- `USE_S3=true` で object storage backend を有効化
- ConoHa Object Storage を想定
- `django-storages` + `boto3` を利用

## 保存対象
- アップロード元ファイル
- 生成レポート
- 将来の成果物ファイル

## 設計上の注意
- アプリケーションコードは storage backend に依存しない
- settings で storage を切替える
- 永続化前提のパスをハードコードしない
