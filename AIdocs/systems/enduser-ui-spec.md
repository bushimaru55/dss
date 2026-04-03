# Enduser UI Spec (MVP)

## 目的
管理者向け Django admin とは分離し、エンドユーザーが以下を完結できる UI を提供する。

1. ログイン
2. Excel/CSV アップロード
3. プレビュー確認
4. 分析候補（suggestions）確認

## 画面構成（MVP）
- `/app/login` : エンドユーザー向けログイン
- `/app/` : ダッシュボード（dataset 一覧）
- `/app/datasets/new` : アップロード画面
- `/app/datasets/{id}` : データ理解画面（preview/profile/semantic/suggestions）

## 設計方針
- Django テンプレートベースで最短実装
- 認証は Django session auth を利用
- 管理画面 `/admin/` とは導線分離
- API は既存 `datasets` / `suggestions` を再利用

## MVPで確認する体験
1. ログインできる
2. ファイルをアップロードできる
3. 「分析準備を実行」で profile + semantic + suggestions が生成される
4. 画面で候補タイトル/説明/優先度が確認できる
