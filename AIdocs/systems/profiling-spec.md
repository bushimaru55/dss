# Profiling Spec

## 目的
データ内容の概要を機械的に抽出し、後続の AI 推定に必要なメタ情報を作る。

## 抽出項目
- row_count
- column_count
- column_name
- inferred_type
- null_ratio
- sample_values

## inferred_type 候補
- string
- number
- date
- unknown
