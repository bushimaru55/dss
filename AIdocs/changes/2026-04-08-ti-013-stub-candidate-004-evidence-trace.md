# 2026-04-08 — 013 stub 候補の 004 根拠トレース（Pattern B）

## 概要

- **`_build_stub_analysis_candidates`**（`services.py`）が返す stub の **`evidence` / `risk_notes`** を、**004 `AnalysisMetadata` 観測**（metadata_id、dataset_id、dimensions/measures の id・name、`time_axis` 有無）で具体化。
- **候補件数・category・priority・readiness・生成条件は不変**。005/011 は候補選定に未使用。
- **OpenAPI 0.1.14-draft**、SPEC-TI-013 / §19.5 追記、テスト追加。

## migration

- なし（`analysis_candidates` JSON の内容拡張のみ）。
