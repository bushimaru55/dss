# 変更記録: GET `/suggestion-runs/.../candidates` に `generation_constraints_reference`

**日付**: 2026-04-08  
**関連**: `table_intelligence.views.SuggestionCandidatesListView`, OpenAPI **0.1.11-draft**, SPEC-TI-013 / SPEC-TI-014

## 概要

`GET /suggestion-runs/{suggestion_run_ref}/candidates` の 200 応答に、**`GET .../suggestion-runs/{ref}`（SuggestionSet detail）と同じ** `build_mvp_013_generation_constraints_reference` 由来の **`generation_constraints_reference`** を**トップレベル**で追加した。候補配列の内容・順序は変更しない（read-only 観測）。

## 境界

- 005 正本 / 011 補助 / 013 参照の整理は [SPEC-TI-014 §20](../specs/table-intelligence/04_system/SPEC-TI-014-api.md#20-未着手境界と次実装前提) および §19 と整合。
- 新 gating・semantic lock-in・候補昇格ロジックは追加していない。
