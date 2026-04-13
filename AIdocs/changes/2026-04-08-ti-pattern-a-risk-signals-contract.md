# 変更記録: Pattern A — `risk_signals` / `auxiliary_signals_from_011` 契約明文化

**日付**: 2026-04-08  
**関連**: SPEC-TI-011 / 013 / 014、OpenAPI **0.1.12-draft**、`test_suggestion_api.py`

## 概要

011 の既存補助 signal（**`risk_signals`** 等）と、013 **`generation_constraints_reference.auxiliary_signals_from_011`** が **read-only 写し**であることを **文書・OpenAPI description・最小テスト**で固定した。**新列・新評価ルール・strict schema 化はなし**。

## OpenAPI

- `TiMvpConfidenceEvaluation` / `Mvp013GenerationConstraintsReference` / `risk_signals` property の **description 補足**。

## テスト

- evaluation detail の `risk_signals` と suggestion detail/candidates の `auxiliary_signals_from_011.risk_signals` の一致（object 要素を含む配列）。
