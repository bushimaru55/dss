# 2026-04-08 — TI: 005 未解決観測の下流 read-only 参照の明文化

## 概要

- **目的**: `mvp_005_canonical_summary.unresolved_work_present` 等が **011**（`review_state_reference`）および **013**（`primary_constraints_from_005`）で **005 由来の read-only 参照**として整合することを、SPEC / OpenAPI / テストで固定する。候補昇格・抑制の**ルール化は行わない**（§20・ガードレール維持）。
- **判定**: **パターン A**（実装は既に十分露出。文書・OpenAPI description・参照整合テストの最小追補）。

## 更新ファイル

- **AIdocs**: `SPEC-TI-005` / `011` / `013` / `014`（§19.3）、`INDEX-table-intelligence.md`
- **OpenAPI**: `table-intelligence-openapi-draft.yaml` **0.1.13-draft**（`Mvp005CanonicalSummary` / `Mvp011ReviewStateReference` / `Mvp013GenerationConstraintsReference` の description）
- **Tests**: `backend/table_intelligence/tests/test_suggestion_api.py`（`unresolved_work_present` の cross-endpoint 整合）

## コード

- **アプリコード変更なし**（ビヘイビア変更なし）。
