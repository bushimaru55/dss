# Profile Generation Verification

## 実施日
2026-03-27

## 確認項目
- row_count
- column_count
- inferred_type
- null_ratio
- sample_values

## 結果
- 成功
- row_count: 3
- column_count: 5
- inferred_type:
  - `order_date`: `date`
  - `amount`: `number`
  - その他列: `string`
- null_ratio:
  - `order_date`: `0.3333`（1/3 が空）
  - その他列: `0.0`
- sample_values:
  - `amount`: `["1200","980","1500"]`
  - `status`: `["open","closed"]`
- 補足:
  - `POST /profile/` 後、`status=mapping_ready` へ遷移（`infer_semantic_columns` まで実行されたことを確認）。
