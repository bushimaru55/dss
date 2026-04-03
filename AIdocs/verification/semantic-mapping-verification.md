# Semantic Mapping Verification

## 実施日
2026-03-27

## 確認項目
- AI 推定保存
- user 修正保存
- source 切替
- profile 再取得時の反映

## 結果
- 成功
- AI 推定保存:
  - 初回 profile 取得時に `semantic_label_source="ai"` が各列に設定済み。
  - 例: `amount -> amount`, `order_date -> date`, `assignee -> assignee`
- user 修正保存:
  - `POST /semantic-mapping/` で `amount`, `status` を更新。
- source 切替:
  - 更新対象列が `semantic_label_source="user"` へ切替。
- profile 再取得時の反映:
  - `GET /profile/` 再実行で `amount/status` が `source=user` で返却されることを確認。
