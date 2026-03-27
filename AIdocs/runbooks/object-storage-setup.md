# Runbook: Object Storage Setup

## 目的
ConoHa Object Storage を media / uploads / reports 用 backend として利用する。

## 必要な環境変数
```env
USE_S3=true
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=...
AWS_S3_ENDPOINT_URL=...
AWS_S3_REGION_NAME=...
AWS_DEFAULT_ACL=
AWS_QUERYSTRING_AUTH=false
```

## 確認手順
1. `USE_S3=true` を設定する
2. web を再起動する
3. Django shell で storage backend を確認する
4. admin または shell から簡易アップロードを行う
5. object storage 側にファイルが作成されることを確認する

## 失敗時の確認観点
- endpoint URL が正しいか
- bucket 名が正しいか
- 認証情報が正しいか
- HTTPS / region 設定が適切か
- `django-storages` の backend 設定が正しいか
