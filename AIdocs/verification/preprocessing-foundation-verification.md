# Verification: Preprocessing Foundation

## 実施日
2026-03-27

## 確認項目
- CSV 読込（文字コード・区切りの基本ケース）
- Excel 読込（シート一覧・結合セル検知）
- preview 取得（rows/header候補/warnings）
- profiling（row/column/null/unique/sample/type）
- semantic mapping 候補生成
- user 修正保存
- pandera 検証エラー整形

## 結果
- 実施結果: 成功（local）
- 自動テスト: `docker compose exec -T web pytest -q` -> `4 passed`
- 確認内容:
  - upload / sheets / preview API: 正常
  - profile API: `rows_count`, `columns_count`, `analysis` 取得
  - semantic-mapping generate + update + get: 正常
  - user 修正で `semantic_label_source=user` に更新
  - pandera validation 結果が `sheet.analysis.schema_validation` に保持
  - DatasetFile が dataset 作成時に生成される
  - ProfilingRun/ProfiledColumn、SemanticMappingRun/SemanticMappingEntry に履歴が残る
  - chat ask API で analysis run が作成され、結果取得APIで answer が返る
  - rag index/search API が動作し、chat evidence に rag_items が含まれる
- 補足:
  - pandas 日付推定の warning（format 推定）が出るため、次段でフォーマット指定の最適化余地あり
