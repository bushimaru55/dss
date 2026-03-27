# Task Flow Phase 2

## 非同期タスク
1. `profile_dataset`
   - ファイル読込
   - 行数/列数算出
   - 列ごとの profile 作成

2. `infer_semantic_columns`
   - profile を入力に AI 推定
   - semantic_label を保存

## 推奨実行順
upload -> select sheet -> profile -> semantic inference -> review
