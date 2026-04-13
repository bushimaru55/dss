# 変更記録: OpenAPI 0.1.9 / SPEC 追補（MVP 読み取り専用参照面）

**日付**: 2026-04-08  
**関連**: `table-intelligence-openapi-draft.yaml`, SPEC-TI-005 / 011 / 013 / 014

## 概要

実装済みの **005 / 011 / 013 読み取り専用参照面**（`mvp_005_canonical_summary`, `review_state_reference`, `generation_constraints_reference`）を、**OpenAPI 叩き台**および **AIdocs** に最小反映した。新しい実行挙動は追加していない。

## OpenAPI（0.1.8-draft → 0.1.9-draft）

- `components.schemas`: `Mvp005CanonicalSummary`, `Mvp011ReviewStateReference`, `Mvp013GenerationConstraintsReference` を追加（`additionalProperties: true`、説明に readOnly 前提を記載）。
- `TiMvpHumanReviewSession`: `mvp_005_canonical_summary` を必須化（MVP 実装と一致）。
- `TiMvpConfidenceEvaluation`: `review_state_reference` を必須化。
- `TiMvpSuggestionSet`: 新規。`GET /suggestion-runs/{ref}` の 200 を **`SuggestionSet` から本スキーマへ**変更。
- `info.description`: 0.1.9 の要点を 1 バレット追記。

## AIdocs

- **SPEC-TI-005**: `mvp_005_canonical_summary`（観測・正本ではない）を節として追記。
- **SPEC-TI-011**: `review_state_reference`（011 数値は不変）を節として追記。
- **SPEC-TI-013**: `generation_constraints_reference`（一次制約／補助の参照のみ）を節として追記。
- **SPEC-TI-014**: **§19** を新設（表と OpenAPI へのポインタ）。
- **INDEX-table-intelligence**: OpenAPI 版表記を 0.1.9-draft に更新。

## 境界（文書上の固定）

- **005 正本**: `HumanReviewSession` / `SuppressionRecord` / snapshot。サマリ JSON は観測用派生。
- **011 補助**: `ConfidenceEvaluation` の列が正本。`review_state_reference` は 005 観測の参照。
- **013**: `generation_constraints_reference` は参照のみ。候補確定・suppression 再定義は行わない。

## 保留

- 提示 gating 語彙の本格化、OpenAPI への `readOnly` プロパティ明示（ツール互換）、`GET .../candidates` への同参照面の要否。
