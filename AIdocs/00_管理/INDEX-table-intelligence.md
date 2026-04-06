# 表インテリジェンス仕様書 索引（SPEC-TI-001〜015 登録欄）

最終更新: 2026-04-07

| ID | 題名 | 版 | 状態 | パス（予定／実在） |
|----|------|-----|------|-------------------|
| SPEC-TI-001 | 表読取仕様書 | 0.2 | Draft | [specs/table-intelligence/02_pipeline/SPEC-TI-001-table-read.md](../specs/table-intelligence/02_pipeline/SPEC-TI-001-table-read.md) |
| SPEC-TI-002 | 判定ロジック仕様書 | 0.2 | Draft | [specs/table-intelligence/02_pipeline/SPEC-TI-002-judgment.md](../specs/table-intelligence/02_pipeline/SPEC-TI-002-judgment.md) |
| SPEC-TI-003 | 変換・正規化仕様書 | 0.2 | Draft | [specs/table-intelligence/02_pipeline/SPEC-TI-003-normalization.md](../specs/table-intelligence/02_pipeline/SPEC-TI-003-normalization.md) |
| SPEC-TI-004 | 分析メタデータ仕様書 | 0.2 | Draft | [specs/table-intelligence/03_analysis_human/SPEC-TI-004-analysis-metadata.md](../specs/table-intelligence/03_analysis_human/SPEC-TI-004-analysis-metadata.md) |
| SPEC-TI-005 | 人確認フロー仕様書 | 0.2 | Draft | [specs/table-intelligence/03_analysis_human/SPEC-TI-005-human-review-flow.md](../specs/table-intelligence/03_analysis_human/SPEC-TI-005-human-review-flow.md) |
| SPEC-TI-006 | 入出力データ仕様書 | 0.5 | Draft | [specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md) |
| SPEC-TI-007 | UI仕様書 | — | 未作成 | ../specs/table-intelligence/05_experience_quality/SPEC-TI-007-ui.md |
| SPEC-TI-008 | テスト仕様書 | — | 未作成 | ../specs/table-intelligence/05_experience_quality/SPEC-TI-008-test.md |
| SPEC-TI-009 | 表分類体系仕様書 | 0.1 | Draft | [specs/table-intelligence/01_foundation/SPEC-TI-009-table-taxonomy.md](../specs/table-intelligence/01_foundation/SPEC-TI-009-table-taxonomy.md) |
| SPEC-TI-010 | 見出しモデル仕様書 | 0.1 | Draft | [specs/table-intelligence/01_foundation/SPEC-TI-010-heading-model.md](../specs/table-intelligence/01_foundation/SPEC-TI-010-heading-model.md) |
| SPEC-TI-011 | 信頼度スコアリング仕様書 | 0.3 | Draft | [specs/table-intelligence/02_pipeline/SPEC-TI-011-confidence-scoring.md](../specs/table-intelligence/02_pipeline/SPEC-TI-011-confidence-scoring.md) |
| SPEC-TI-012 | エラー処理・例外仕様書 | 0.1 | Draft | [specs/table-intelligence/01_foundation/SPEC-TI-012-errors.md](../specs/table-intelligence/01_foundation/SPEC-TI-012-errors.md) |
| SPEC-TI-013 | 分析候補生成仕様書 | 0.2 | Draft | [specs/table-intelligence/03_analysis_human/SPEC-TI-013-suggestion-generation.md](../specs/table-intelligence/03_analysis_human/SPEC-TI-013-suggestion-generation.md) |
| SPEC-TI-014 | API仕様書 | 0.1 | Draft | [specs/table-intelligence/04_system/SPEC-TI-014-api.md](../specs/table-intelligence/04_system/SPEC-TI-014-api.md) |
| SPEC-TI-015 | DB設計仕様書 | 0.1 | Draft | [specs/table-intelligence/04_system/SPEC-TI-015-db-design.md](../specs/table-intelligence/04_system/SPEC-TI-015-db-design.md) |

## 計画・規約

- [実装前レビュー観点整理](実装前レビュー観点整理_table-intelligence.md)（実装着手前のチェックリスト・アジェンダ、`0.1`）
- [API × DTO × DB 対応表](API_DTO_DB対応表_table-intelligence.md)（014 / 006 / 015 / OpenAPI / DDL の横断ブレ止め、`0.1`）
- [OpenAPI 叩き台（draft）](../specs/table-intelligence/04_system/openapi/table-intelligence-openapi-draft.yaml)（SPEC-TI-014＋006 の機械可読ドラフト、`0.1.0-draft`）
- [DDL 叩き台（draft）](../specs/table-intelligence/04_system/sql/table-intelligence-ddl-draft.sql)（SPEC-TI-015 ベースの PostgreSQL 初期 DDL、`0.1.0-draft`）
- [表解析仕様群_最終整合レビュー完了報告.md](表解析仕様群_最終整合レビュー完了報告.md)（仕様フェーズの節目・引き継ぎ）
- [仕様書作成計画.md](仕様書作成計画.md)
- [表解析コア仕様レビュー整理メモ.md](表解析コア仕様レビュー整理メモ.md)
- [文書管理規約.md](文書管理規約.md)
- [用語集-glossary.md](用語集-glossary.md)（スタブ）

## Phase 対応

- Phase 1: 009, 010, 006, 012（骨格）
- Phase 2: 011, 001, 002, 003
- Phase 3: 004, 005, 013
- Phase 4: 006 拡張, 014, 015, 012 完成
- Phase 5: 007, 008
