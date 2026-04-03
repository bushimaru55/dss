# Datasets Spec

## 概要
Dataset は、アップロードされたファイルとそのメタ情報を保持する。

## 主な責務
- ファイルアップロード
- file_type 判定
- シート一覧取得
- プレビュー保持（rows/columns/summary）
- 処理ジョブ状態管理（queued/running/succeeded/failed）
- status 管理

## 推奨 status
- uploaded
- profiling
- profiled
- mapping_ready
- error
