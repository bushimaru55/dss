---
title: API_DTO_DB対応表_table-intelligence
status: Draft
version: 0.1
last_updated: 2026-04-07
---

## 1. 文書情報

| 項目 | 値 |
|------|-----|
| 文書名 | API × DTO × DB 対応表（表インテリジェンス） |
| 版 | 0.1 |
| 状態 | Draft |
| 最終更新 | 2026-04-07 |
| 位置づけ | **実装接続前の横断ブレ止め用管理表**（006 / 014 / 015 / OpenAPI / DDL のいずれも正本ではない） |

---

## 2. 目的

- **API リソース**（014）、**DTO**（006）、**DB**（015）、および **OpenAPI 叩き台**・**DDL 叩き台**の対応を **一枚で追跡**する。
- **request / response**、**主テーブル / カラム**、**ID・ref の橋渡し**、**正本仕様**を同じ表組で見える化する。
- **差分・未確定点**（OpenAPI / DDL の TODO、enum 未確定など）を隠さず載せ、実装者・レビュア・仕様側の **共通参照面**にする。

---

## 3. 参照元

| 種別 | パス |
|------|------|
| API 契約（正本） | [SPEC-TI-014-api.md](../specs/table-intelligence/04_system/SPEC-TI-014-api.md) |
| DTO / データ契約（正本） | [SPEC-TI-006-io-data.md](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md) |
| DB 設計（正本） | [SPEC-TI-015-db-design.md](../specs/table-intelligence/04_system/SPEC-TI-015-db-design.md) |
| OpenAPI 叩き台 | [table-intelligence-openapi-draft.yaml](../specs/table-intelligence/04_system/openapi/table-intelligence-openapi-draft.yaml)（`0.1.0-draft`） |
| DDL 叩き台 | [table-intelligence-ddl-draft.sql](../specs/table-intelligence/04_system/sql/table-intelligence-ddl-draft.sql)（`0.1.0-draft`） |

---

## 4. 対応表の見方

- **ベースパス**: OpenAPI `servers` は `…/v1`。本表の path は **`/v1` プレフィックス付き**で記載（014 §8〜11 と整合）。
- **実行系**: POST で **`job_id` / `suggestion_run_ref` 等を発行**。本体は GET で再取得（014 §4.2）。
- **参照系**: GET で **006 準拠の実体**または **サマリ / 一覧**。
- **正本仕様**列: **挙動・意味の正本**を示す。OpenAPI / DDL は **機械可読叩き台**であり、**列挙・HTTP 詳細の最終確定は 006 / 014 / 015 および次版 OpenAPI**に委ねる。
- **OpenAPI / DDL 状態**: 「定義済み」は **叩き台に該当 path・テーブルがある**こと。**TODO あり**はファイル内コメントの残タスクを指す。

---

## 5. API × DTO × DB 対応表

### 5.1 Jobs（実行系）

| 区分 | API / operation | request DTO（006 準拠・OpenAPI 名） | response DTO（OpenAPI 名） | 主要 ID / ref | 主テーブル（DDL） | 主要カラム / 関係 | OpenAPI | DDL | 正本仕様 | 備考 |
|------|-----------------|--------------------------------------|----------------------------|---------------|-------------------|-------------------|---------|-----|----------|------|
| 実行 | `POST /v1/table-analysis/jobs` | `StartAnalysisJobRequest` | `JobAcceptedResponse` / `202` | `job_id`（発行） | `analysis_job` | `job_id`, `workspace_id`, `status`, `kind`, `table_id`, `idempotency_key`, `input_parameters` | 定義済み | 定義済み | **014 §8**, **006 JobRun** | 受理後非同期。`evaluation_ref` / `suggestion_run_ref` は完了時にジョブ行へ載りうる（006 / 015）。 |
| 参照 | `GET /v1/table-analysis/jobs/{job_id}` | — | `JobDetail` / `JobSummary` | `job_id`, 確定 ref 部分集合 | `analysis_job`（+ `job_stage_run` で詳細化可） | `status`, `table_id`, `evaluation_ref`, `suggestion_run_ref`, `error_code` | 定義済み | 定義済み | **014 §8** | OpenAPI は `JobDetail`。DDL に `evaluation_ref` / `suggestion_run_ref` 列（API 慣用名; 値は `evaluation_id` / `suggestion_run_id` と同一キー空間）。 |
| 実行 | `POST /v1/table-analysis/jobs/{job_id}/rerun` | `RerunJobRequest` | `JobAcceptedResponse` 等 | `job_id` | `analysis_job`, `job_stage_run` | `input_parameters`（jsonb）, 段階は `job_stage_run.stage` | 定義済み | 定義済み | **014 §8**, **015 §7.1–7.2** | 段階指定の詳細は **014 次版**。DDL `job_stage_run` に TODO（一意制約など）。 |

### 5.2 Tables / Artifacts（参照系）

| 区分 | API / operation | request DTO | response DTO | 主要 ID / ref | 主テーブル | 主要カラム / 関係 | OpenAPI | DDL | 正本仕様 | 備考 |
|------|-----------------|-------------|--------------|---------------|------------|-------------------|---------|-----|----------|------|
| 参照 | `GET /v1/tables/{table_id}` | — | `TableSummary` | `table_id` | `table_scope` | `workspace_id`, `source_id`, `document_id`, `bbox` | 定義済み | 定義済み | **014 §9**, **015 §7.3** | 001 観測アンカー。 |
| 参照 | `GET /v1/tables/{table_id}/read-artifact` | — | `TableReadArtifact` | `table_id`, `artifact_id` | `table_read_artifact` | `cells`, `merges`, `parse_warnings`（jsonb）, `artifact_version`, `is_latest` | 定義済み | 定義済み | **001**, **006 TableReadArtifact**, **015 §7.4** | 大ペイロードは 014 次版で部分取得等の余地あり。 |
| 参照 | `GET /v1/tables/{table_id}/decision` | — | `JudgmentResult`（内包 `DecisionJudgment`） | `table_id`, `judgment_id` | `judgment_result` | **`decision`**（002）, `evidence`（jsonb） | 定義済み | 定義済み | **002**, **006 JudgmentResult**, **015 §7.5** | **`decision_recommendation` はここに含めない**（011 は `confidence_evaluation`）。 |
| 参照 | `GET /v1/tables/{table_id}/artifacts` | — | `ArtifactRefsList` | `table_id`, 各種 ref | 複数 + **`artifact_relation`** | lineage / SUPERSEDES（015 §7.14） | 定義済み | `artifact_relation` 定義済み | **014 §9**, **015 §7.14, §10** | GET 実装は **集約ビュー or アプリ結合**。多型 `from_id`/`to_id` は FK なし（DDL TODO）。 |
| 参照 | `GET /v1/datasets/{dataset_id}` | — | `NormalizedDataset` | `dataset_id`, `table_id` | `normalized_dataset` | `rows`, `trace_map`（jsonb）, `normalization_status` | 定義済み | 定義済み | **003**, **006 NormalizedDataset**, **015 §7.6** | `metadata_id` とは別成果物。 |
| 参照 | `GET /v1/metadata/{metadata_id}` | — | `AnalysisMetadata` | `metadata_id`, `dataset_id` | `analysis_metadata` | `dataset_id` FK, `review_points`（jsonb）, `dimensions`, `measures` | 定義済み | 定義済み | **004**, **006 AnalysisMetadata**, **015 §7.7** | 004 の **`review_required` / `review_points`** が 005 の主入力。 |
| 参照 | `GET /v1/metadata/{metadata_id}/review-points` | — | `ReviewPoint[]`（例） | `metadata_id` | `analysis_metadata.review_points` | `review_points` jsonb（列） | 定義済み | 定義済み | **004**, **005**（発生条件） | 別リソース化は **正規化テーブル後続**（015 §16）。 |
| 参照 | `GET /v1/evaluations/{evaluation_ref}` | — | `ConfidenceEvaluation`（内包 `DecisionRecommendation`） | **`evaluation_ref`**（= **`evaluation_id`**） | `confidence_evaluation` | **`decision_recommendation`**（011）, `scores`, `explanation`（jsonb） | 定義済み | 定義済み | **011**, **006 ConfidenceEvaluation**, **015 §7.10** | パスは API 名 **`evaluation_ref`**。DB PK 列は **`evaluation_id`**（同一値）。**002 の `decision` は保持しない**。 |

### 5.3 Review（人確認）

| 区分 | API / operation | request DTO | response DTO | 主要 ID / ref | 主テーブル | 主要カラム / 関係 | OpenAPI | DDL | 正本仕様 | 備考 |
|------|-----------------|-------------|--------------|---------------|------------|-------------------|---------|-----|----------|------|
| 実行 | `POST /v1/review-sessions` | `CreateReviewSessionRequest` | `HumanReviewSession`（作成結果） | `session_id`（発行）, `metadata_id` | `human_review_session` | `metadata_id` FK, `state`, `pending_questions` | 定義済み | 定義済み | **005**, **006 HumanReviewSession**, **015 §7.8** | 005 の状態機械が正本。API は窓口。 |
| 参照 | `GET /v1/review-sessions/{session_id}` | — | `HumanReviewSession` | `session_id`, `metadata_id` | `human_review_session` | 同上 + `pending_job_id` → `analysis_job` | 定義済み | 定義済み | **005**, **006**, **015 §7.8** | **`review_session_id` は採用しない**（014 / 015 / 006 統一）。 |
| 実行 | `POST /v1/review-sessions/{session_id}/answers` | `SubmitReviewAnswersRequest` | 受理レスポンス | `session_id`, `answer_id` | `human_review_answer` | `point_id`, `client_nonce`, `answered_by` | 定義済み | 定義済み | **005**, **006 answers[]**, **015 §7.9** | 冪等は **014 §4.5 / 015** で次版確定。DDL に UNIQUE `(session_id, client_nonce)`（TODO あり）。 |
| 実行 | `POST /v1/review-sessions/{session_id}/rerun` | （014 ペイロード次版） | `JobAcceptedResponse` 等 | `session_id`, 新 `job_id` | `human_review_session`, `analysis_job` | `pending_job_id`, 新ジョブ行 | 定義済み | 定義済み | **014 §8, §10**, **005** | review 後 rerun。 |
| 参照 | `GET /v1/review-sessions/{session_id}/suppression` | — | `SuppressionStateResponse` | `session_id` | **`suppression_record`**（主） | `point_id`, `suppression_kind`, `context`（jsonb） | 定義済み | 定義済み | **005（suppression 正本）**, **015 §7.13, 付録 A** | **`suggestion_set.suppression_applied`** は **005 を読んだ結果の投影**。正本は **005 + `suppression_record`**。 |

### 5.4 Suggestions（013）

| 区分 | API / operation | request DTO | response DTO | 主要 ID / ref | 主テーブル | 主要カラム / 関係 | OpenAPI | DDL | 正本仕様 | 備考 |
|------|-----------------|-------------|--------------|---------------|------------|-------------------|---------|-----|----------|------|
| 実行 | `POST /v1/suggestion-runs` | **`StartSuggestionRunRequest`（`metadata_id` 必須寄り）** | 受理 + **`suggestion_run_ref`** | **`suggestion_run_ref`**（= `suggestion_run_id`）, **`metadata_id`** | `suggestion_set` | **`metadata_id` NOT NULL**, `dataset_id`, `evaluation_id`, `session_id` NULL 可 | 定義済み | 定義済み | **013**, **006 SuggestionSet**, **015 §7.11（方針 A）** | **主入力は `metadata_id`**。`dataset_id` は補助。013 は **004 を主入力**し **011 / 005 を読む**。 |
| 参照 | `GET /v1/suggestion-runs/{suggestion_run_ref}` | — | `SuggestionSet` | **`suggestion_run_ref`** | `suggestion_set` | `analysis_candidates`（jsonb）, `suppression_applied`（jsonb） | 定義済み | 定義済み | **013**, **006**, **015 §7.11** | PK 列名は **`suggestion_run_id`**（DB）= API **`suggestion_run_ref`**（同一値）。 |
| 参照 | `GET /v1/suggestion-runs/{suggestion_run_ref}/candidates` | クエリ `suppression`, `include` 等 | `SuggestionCandidate[]` 等 | 同上 | `suggestion_set`（+ 将来 `suggestion_candidate`） | `analysis_candidates` またはサテライト | 定義済み | **サテライト省略**（TODO） | **013**, **005**（suppression 適用時） | DDL は **候補を jsonb 一括**可。**`suppression=applied` は 005 状態を読んだ結果**（014 §11）。 |

### 5.5 `decision` と `decision_recommendation`（横断）

| 概念 | 正本仕様 | DTO（006） | API（014 / OpenAPI） | DB 列（DDL） |
|------|----------|------------|----------------------|--------------|
| **`decision`**（一次判定） | **002** | `JudgmentResult` | `GET .../decision` → `JudgmentResult` / `DecisionJudgment` | **`judgment_result.decision`** |
| **`decision_recommendation`**（011 推奨） | **011** | `ConfidenceEvaluation` | `GET .../evaluations/{evaluation_ref}` → `DecisionRecommendation` 相当 | **`confidence_evaluation.decision_recommendation`** |

**混在禁止**（014 §5.4, 015 §7.5, §7.10）。

### 5.6 suppression の流れ（正本 vs 投影）

| 層 | 内容 | 正本仕様 |
|----|------|----------|
| 業務・状態 | 抑制の意味・遷移 | **005** |
| DB 推奨保持 | 行単位の抑制 | **`suppression_record`**（015 付録 A） |
| API | 参照窓口 | `GET .../suppression` |
| suggestion | 候補への反映説明 | `SuggestionSet` の **`suppression_applied`**（**005 を読んだ投影**; 正本は 005 + `suppression_record`） |

---

## 6. ID / ref 橋渡し整理

### 6.1 中心 ID（006 / 014 / 015 共通語彙）

| 語彙 | 006 | API / OpenAPI | DB（DDL） | 備考 |
|------|-----|---------------|-----------|------|
| `job_id` | `JobRun.job_id` | パス・ジョブ応答 | `analysis_job.job_id` | |
| `table_id` | テーブル候補・成果物 | パス | `table_scope.table_id` ほか FK | 横断アンカー |
| `dataset_id` | `NormalizedDataset` | パス | `normalized_dataset.dataset_id` | 003 主成果物 |
| `metadata_id` | `AnalysisMetadata` | パス | `analysis_metadata.metadata_id` | 004 主成果物。**003 従属**（`metadata.dataset_id` FK） |
| `session_id` | `HumanReviewSession.session_id` | パス | `human_review_session.session_id` | **`review_session_id` は不採用** |
| **`evaluation_ref`** | `ConfidenceEvaluation.evaluation_id` と同一キー | **パス・ジョブ上の API 名** | 列名 **`evaluation_id`**（`confidence_evaluation` PK） | **値は同一**（015 §5.2） |
| **`suggestion_run_ref`** | `SuggestionSet.suggestion_run_id` と同一キー | **パス・ジョブ上の API 名** | 列名 **`suggestion_run_id`**（`suggestion_set` PK） | **値は同一**（015 §5.2） |

### 6.2 補助・世代（015）

| 語彙 | 主な所在（DDL） | 備考 |
|------|-----------------|------|
| `artifact_version` | 各 artifact 系 | 単調増加・世代 |
| `is_latest` | 同上 | クエリ最適化用。**真実は supersede 鎖**（015 §10） |
| `superseded_by` / `superseded_at` | 同上 | immutable 寄り運用 |
| `artifact_relation` | `from_*`, `to_*`, `relation_kind` | rerun / lineage。**多型のため FK は DDL では未張り**（TODO） |

---

## 7. 主要な未確定事項

| 領域 | 内容 | 主な参照 |
|------|------|----------|
| HTTP | ステータスと **012 `error_code`** の対応 | OpenAPI `info` TODO、014 §13 |
| OpenAPI | 認証スキーム、ページネーション詳細 | OpenAPI TODO |
| DDL | **CHECK** の列挙（`status`, `kind`, `state`, `normalization_status` 等）と **006 完全一致** | DDL ファイル TODO、006 §6 |
| DDL | `(workspace_id, idempotency_key)` 部分一意、`job_stage_run` 一意 | DDL TODO、015 §7 |
| DDL | `suggestion_candidate` サテライトの要否 | DDL コメント（015 §7.12） |
| DDL | RLS / テナント境界 | DDL TODO、015 §13 |
| 014 | **`PATCH /review-sessions/{session_id}`**（state 遷移）は **§10 に論理操作として記載**あるが、**叩き台 OpenAPI には `patch` 未収録** | 014 §10 vs OpenAPI |
| 候補取得 | `GET .../candidates` のクエリ正式名 | 014 §11 |

---

## 8. 次工程への引き継ぎメモ

- **実装前レビュー**で本表を固定し、**006 フィールド名**・**014 論理 path**・**015 テーブル**・**OpenAPI operationId** の **ズレを差分リスト化**する。
- **マイグレーション**は DDL 叩き台をベースに、**enum / 一意制約 / RLS** を要件確定後に追加。
- **OpenAPI** は 014 の HTTP 詳細確定に合わせて **response コードと 012 の対応表**を埋める。
- **対応表自身**の版上げタイミング: **006 または 014 の改訂**、または **OpenAPI/DDL のメジャー更新**時。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-07 | 初版。014 / 006 / 015 / OpenAPI / DDL の横断対応表。 |
