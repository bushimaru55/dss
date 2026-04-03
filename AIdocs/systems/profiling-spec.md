# Profiling Spec

## 目的
データ内容の概要を機械的に抽出し、後続の AI 推定に必要なメタ情報を作る。

## 抽出項目
- row_count
- column_count
- column_name
- normalized_name
- inferred_type
- null_ratio
- unique_ratio
- sample_values
- warnings
- detected_header_row
- detected_data_start_row
- sheet_analysis（merged_cells, table_like など）

## inferred_type 候補
- string
- number
- date
- unknown

## 検証
- pandera による汎用スキーマ検証
- 売上系 / 顧客系のサンプルスキーマ候補
