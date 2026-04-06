---
id: SPEC-TI-015
title: DB設計仕様書
status: Draft
version: 0.1
owners: []
last_updated: 2026-04-07
depends_on:
  - SPEC-TI-001
  - SPEC-TI-002
  - SPEC-TI-003
  - SPEC-TI-004
  - SPEC-TI-005
  - SPEC-TI-006
  - SPEC-TI-011
  - SPEC-TI-012
  - SPEC-TI-013
  - SPEC-TI-014
---

## 1. 文書情報

| 項目 | 値 |
|------|-----|
| 文書 ID | SPEC-TI-015 |
| 題名 | DB 設計仕様書（表解析パイプライン永続化） |
| 版 | 0.1 |
| 状態 | Draft |
| 最終更新 | 2026-04-07 |

本版は **エンティティ粒度・主要カラム・参照制約・世代管理方針**までを定義する。**DDL の完全確定**（型の最終選定、パーティション、細かい CHECK の網羅）は **実装リポジトリのマイグレーション**で確定する。

---

## 2. 目的と適用範囲

### 2.1 目的

本仕様書は、**SPEC-TI-014** の API 契約および **SPEC-TI-006** のデータ契約を、**責務境界を崩さず永続化可能にする**ための **DB 設計の正本**である。

一言で表すと、**「014 の API と 006 の型を、実装接続フェーズで安全に載せるための永続化設計」** である。

### 2.2 対象範囲

- **テーブル／エンティティ粒度**、**主キー・外部キー方針**、**世代（superseded）と latest 解決**。
- **job／run 系**と **artifact 系**の分離、**relation／control 系**。
- **JSON カラムの許容範囲**と **列正規化の境界**。
- **index 方針**（初版レベル）、**監査・権限・論理削除**の方針。

### 2.3 非対象範囲

- 001〜005・011・013 の **アルゴリズム本文**。
- 014 の **HTTP パス・ステータスコードの最終表**（014 正本）。
- 006 の **JSON Schema の完全パッケージ**（006 Phase 4）。
- **具体的なクラウド SKU・レプリカ構成**。

### 2.4 責務境界（本書の立ち位置）

| 仕様 | 本書との関係 |
|------|----------------|
| 006 | **フィールド意味・列挙の正本**。DB 列名は **一致させるか、明示マッピング**する。無断で意味を変えない。 |
| 014 | **API resource と DB entity の対応**の受け先。API 契約を **上書きしない**。 |
| 005 | **suppression・状態遷移の正本**。DB は **保持と制約可能な範囲**で表現し、**禁止遷移の完全定義**は 005 に残す。 |
| 011 | **`decision_recommendation`・`scores`・`explanation` 構造の正本**。 |
| 013 | **候補内容の意味の正本**。DB は **suggestion_run／set／candidate** の格納構造を定義する。 |

---

## 3. 参照仕様

| ID | 文書 |
|----|------|
| SPEC-TI-001 | [表読取仕様書](../02_pipeline/SPEC-TI-001-table-read.md) |
| SPEC-TI-002 | [判定ロジック仕様書](../02_pipeline/SPEC-TI-002-judgment.md) |
| SPEC-TI-003 | [変換・正規化仕様書](../02_pipeline/SPEC-TI-003-normalization.md) |
| SPEC-TI-004 | [分析メタデータ仕様書](../03_analysis_human/SPEC-TI-004-analysis-metadata.md) |
| SPEC-TI-005 | [人確認フロー仕様書](../03_analysis_human/SPEC-TI-005-human-review-flow.md) |
| SPEC-TI-006 | [入出力データ仕様書](../01_foundation/SPEC-TI-006-io-data.md) |
| SPEC-TI-011 | [信頼度スコアリング仕様書](../02_pipeline/SPEC-TI-011-confidence-scoring.md) |
| SPEC-TI-012 | [エラー処理・例外仕様書](../01_foundation/SPEC-TI-012-errors.md) |
| SPEC-TI-013 | [分析候補生成仕様書](../03_analysis_human/SPEC-TI-013-suggestion-generation.md) |
| SPEC-TI-014 | [API 仕様書](./SPEC-TI-014-api.md) |

---

## 4. DB 設計原則

1. **job／run 系と artifact 系を分離**する。実行履歴と成果物のライフサイクルが異なるため。
2. **成果物は immutable 寄り**とする。**更新より再生成**し、旧行は **superseded** で残す（物理削除は原則しない）。
3. **006 の列挙・意味**を尊重し、**002 の `decision` と 011 の `decision_recommendation` は別列／別行**で混在させない。
4. **頻出検索キー・状態・主要 enum は列**とする。**深いネスト・可変 payload は JSON** に逃がしうる。
5. **014 の resource 粒度**を **極端に潰さない**（1 resource ≒ 1 主たるテーブルまたは明確な親子）。
6. **監査・再実行・差分追跡**に耐えるよう、`job_id`・`created_at`・`superseded_by`・`artifact_relation` を組み合わせる。
7. **DDL 完全確定は本書の次工程**とする。本書は **そのまま DDL に落とせる粒度**を目標とする。

---

## 5. エンティティ全体像

### 5.1 大分類

| 分類 | 代表テーブル（論理名） | 役割 |
|------|------------------------|------|
| **job／run 系** | `analysis_job`, `job_stage_run`, `suggestion_run`, `evaluation_run`（任意） | 非同期実行、段階、外部 ref の発行元 |
| **artifact 系** | `table_scope`, `table_read_artifact`, `judgment_result`, `normalized_dataset`, `analysis_metadata`, `human_review_session`, `human_review_answer`, `confidence_evaluation`, `suggestion_set`, `suggestion_candidate` | 006 に対応する永続化単位 |
| **relation／control 系** | `artifact_relation`, `suppression_record`, `audit_log` | lineage、抑制、監査 |

### 5.2 用語（表記の固定）

| 用語 | 説明 |
|------|------|
| `session_id` | **006 `HumanReviewSession.session_id` のみ**を指す。`review_session_id` という別 ID は **定義しない**。 |
| `evaluation_ref` | API・`JobRun` 上の参照名。**DB 上の主キー列名は `evaluation_id`** とし、**値は同一**（006 `ConfidenceEvaluation.evaluation_id`）。 |
| `suggestion_run_ref` | API・`JobRun` 上の参照名。**DB 上の主キー列名は `suggestion_run_id`** とし、**値は同一**（006 `SuggestionSet.suggestion_run_id`）。 |
| `decision` | **002 Judgment** の列挙。**011 の推奨とは別**。 |
| `decision_recommendation` | **011** の列挙。**002 の `decision` とは別列・別セマンティクス**。 |

**API 契約上の用語**（パス・ジョブ応答での **`evaluation_ref` / `suggestion_run_ref`** 等）の整理は **014 §5**。**値は本表の `evaluation_id` / `suggestion_run_id` と同一キー空間**である。

---

## 6. 識別子・キー方針

### 6.1 中心語彙（006／014 との一致）

| ID | DB における扱い |
|----|-----------------|
| `workspace_id` | 全テーブルで **テナント分離**に使用（006 任意フィールドと整合）。 |
| `job_id` | `analysis_job`（または同等）の **PK**。`job_run` 系から参照。 |
| `table_id` | **横断アンカー**。`table_scope` または先頭 artifact の PK。**複数成果物行に繰り返し出現**する。 |
| `dataset_id` | **`normalized_dataset` の PK**。**003 の主成果物**。`metadata_id` と **別物**（1:1 を基本としつつ世代で 1:N になりうる）。 |
| `metadata_id` | **`analysis_metadata` の PK**。**004 の主成果物**。必ず **`dataset_id` への FK**（同一世代のペア）。 |
| `session_id` | **`human_review_session` の PK**。**005**。 |
| `evaluation_id` | **`confidence_evaluation` の PK**。API の **`evaluation_ref` と同値**。 |
| `suggestion_run_id` | **`suggestion_run` および／または `suggestion_set` の実行単位 PK**。API の **`suggestion_run_ref` と同値**。 |

### 6.2 補助識別子

| 項目 | 用途 |
|------|------|
| `artifact_version` | 同一 `table_id` 上の **論理版**（整数または時刻ベース）。**latest 解決**に使用。 |
| `source_id` / `document_id` | アップロード原本束ね。**014 の命名に従う**（015 では列として保持）。 |
| `superseded_by` | 新 PK への **置換リンク**（同一論理系の次世代）。 |
| `superseded_at` | 置換時刻。 |
| `is_latest` | **その `table_id`（＋種別）における最新行**フラグ（**非正規化キャッシュ**として任意。真実は世代鎖）。 |
| `created_by` / `updated_by` | 監査。**immutable 成果物は `updated_by` を持たない**運用もありうる。 |

---

## 7. テーブル設計

以下、**論理テーブル名**で記載する。物理名は実装で snake_case に統一してよい。

### 7.1 `analysis_job`

| 項目 | 内容 |
|------|------|
| 役割 | **014 の実行 API**に対応する **ジョブ単位**。`job_id` を発行し、非同期状態を保持。 |
| 主キー | `job_id` |
| 主要カラム | `workspace_id`, `status`（006 `JobRun.status` 準拠）, `kind`（`READ`／`JUDGE`／…）, `table_id`（確定後）, `source_id`／`document_id`, `idempotency_key`, `error_code`（012）, `created_at`, `completed_at` |
| 外部参照 | `table_id` → `table_scope`（任意・確定後 FK） |
| 一意制約候補 | `(workspace_id, idempotency_key)` の **部分一意**（一定時間窓・実装依存） |
| 任意／必須 | `table_id`, `evaluation_ref`, `suggestion_run_ref` は **ジョブ完了過程で nullable** |
| JSON 候補 | `input_parameters`（段階指定 rerun の詳細） |
| latest／superseded | **対象外**（ジョブは **履歴として追加**され、キャンセルは状態で表す） |
| 備考 | **`evaluation_ref`／`suggestion_run_ref`** は 006 に合わせ **列として重複保持**してよい（ジョブ完了時のスナップショット）。値は **`evaluation_id`／`suggestion_run_id` と同じ文字列**。 |

### 7.2 `job_stage_run`

| 項目 | 内容 |
|------|------|
| 役割 | **001〜004 等の段階別**の実行行（監査・再実行の細粒度）。 |
| 主キー | `job_stage_run_id` |
| 主要カラム | `job_id` FK, `stage`（`READ`／`JUDGE`／`NORMALIZE`／`META` 等）, `status`, `started_at`, `ended_at`, `output_dataset_id`, `output_metadata_id`（段階で確定したら） |
| 外部参照 | `job_id`, 任意で成果物 ID |
| 一意制約候補 | `(job_id, stage, artifact_version)`（再試行ポリシー次第） |
| JSON 候補 | `stage_detail` |
| 備考 | **必須ではない**が、**rerun 単位の説明**に有効。 |

### 7.3 `table_scope`

| 項目 | 内容 |
|------|------|
| 役割 | **`table_id` の安定したアンカー行**（001 観測対象のコンテナ）。 |
| 主キー | `table_id` |
| 主要カラム | `workspace_id`, `source_id`／`document_id`, `sheet_id`, `bbox`（006 座標系）, `created_at` |
| 外部参照 | `source_id` → 原本ストレージ（別テーブルでも可） |
| latest／superseded | **基本は不変**。同一ドキュメント内の別 bbox は **別 `table_id`** とする（006 に従う）。 |

### 7.4 `table_read_artifact`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `TableReadArtifact`。 |
| 主キー | `artifact_id`（006） |
| 主要カラム | `table_id` FK, `artifact_version`, `is_latest`, `superseded_by`, `cells`／`merges`／`parse_warnings` の **JSON または外部 BLOB 参照** |
| 一意制約候補 | `(table_id, artifact_version)` |
| JSON | `cells` 等 **大容量は JSON またはオブジェクトストレージキー**（実装選択） |

### 7.5 `judgment_result`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `JudgmentResult`。 |
| 主キー | `judgment_id` |
| 主要カラム | `table_id` FK, **`decision`**（002 enum）, `taxonomy_code`, `artifact_version`, `is_latest`, `superseded_by` |
| **禁止** | **`decision_recommendation` を本テーブルに持たせない**（011 は `confidence_evaluation` 側）。 |
| JSON | `evidence`（006 配列。詳細は JSON） |

### 7.6 `normalized_dataset`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `NormalizedDataset`。**`dataset_id` = PK**。 |
| 主キー | `dataset_id` |
| 主要カラム | `table_id` FK, `normalization_status`（§6 enum）, `artifact_version`, `is_latest`, `superseded_by`, `rows`／`trace_map` の **JSON またはハイブリッド** |
| 外部参照 | `table_id` 必須 |
| 備考 | **004 の `metadata_id` は別行**。**dataset と metadata は別成果物**。 |

### 7.7 `analysis_metadata`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `AnalysisMetadata`。 |
| 主キー | `metadata_id` |
| 主要カラム | **`dataset_id` FK（必須）**, `table_id` FK（冗長だが検索用に許容）, `grain`, `artifact_version`, `is_latest`, `superseded_by` |
| 列 | `dimensions[]`／`measures[]` の **JSON または正規化サテライト**（初版は JSON 可） |
| JSON | **`review_points` は 006 準拠で JSON**（または `review_point` サテライトは後続） |

### 7.8 `human_review_session`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `HumanReviewSession`。 |
| 主キー | **`session_id`**（006 と同一） |
| 主要カラム | `workspace_id`, `table_id` FK, **`metadata_id` FK（必須に近い）**, **`state`**（006 §6 enum）, `pending_questions` JSON, `created_at`, `updated_at` |
| suppression | **005 正本**。DB では **§7.12 と併用**（行内 JSON **または** `suppression_record` への FK）。 |
| JSON | `answers` は **`human_review_answer` に正規化**するのを推奨（§7.9）。セッション行に **集約 JSON** を持つと検索が弱い。 |

### 7.9 `human_review_answer`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `answers[]` の **1 行 1 回答**。 |
| 主キー | `answer_id` |
| 主要カラム | **`session_id` FK**, `point_id`, `answer_type`, `selected_option`, `free_text`, `region_ref` JSON, `answered_by`, `answered_at` |
| 一意制約候補 | **冪等**: `(session_id, client_nonce)` 等（014 次版と整合） |

### 7.10 `confidence_evaluation`

| 項目 | 内容 |
|------|------|
| 役割 | 006 `ConfidenceEvaluation`。 |
| 主キー | **`evaluation_id`**（**= API `evaluation_ref`**） |
| 主要カラム | `table_id` FK, **`metadata_id` FK（推奨）**, `dataset_id` FK（任意）, **`decision_recommendation`**（011 enum）, `artifact_version`, `is_latest`, `superseded_by` |
| **禁止** | **002 の `decision` を本テーブルに格納しない**（`judgment_result` へ）。 |
| JSON | `scores`, `explanation`（011 構造）, `feature_snapshot_hash` 列 |

### 7.11 `suggestion_run` / `suggestion_set`

| 項目 | 内容 |
|------|------|
| 役割 | **013 実行単位**と **成果物束**。006 では **`SuggestionSet` に `suggestion_run_id` が含まれる**ため、**最小構成は `suggestion_set` 1 テーブル**で **`suggestion_run_id` を PK** とし、**`suggestion_run` を別テーブルにしない**選択も可。 |
| **方針 A（推奨・初版）** | **`suggestion_set` のみ**: PK **`suggestion_run_id`**（= **`suggestion_run_ref`**）, `table_id`, **`metadata_id` FK（主入力・必須）**, `evaluation_id` FK（任意）, `session_id` FK（任意）, `suppression_applied` JSON, `created_at` |
| **方針 B** | **`suggestion_run`**（メタのみ）＋**`suggestion_set`**（payload）に分割。大 run のみ必要なら B。 |
| JSON | `analysis_candidates` 全体を **JSON**、または **`suggestion_candidate` に正規化**（§7.12）。 |

### 7.12 `suggestion_candidate`（任意サテライト）

| 項目 | 内容 |
|------|------|
| 役割 | 候補 **1 件 1 行**。フィルタ・並び替えを DB で行う場合に有効。 |
| 主キー | `candidate_id` |
| 主要カラム | **`suggestion_run_id` FK**, `category`, `priority`, `confidence`（スカラーまたは JSON）, `readiness` |
| JSON | `evidence`, `risk_notes`, `followup_questions` |
| 備考 | **初版は `suggestion_set` に JSON 一括でも可**。負荷・検索要件でサテライト化。 |

### 7.13 `suppression_record`

| 項目 | 内容 |
|------|------|
| 役割 | **005 の suppression の正本を DB で保持**するための **推奨テーブル**（§9 参照）。 |
| 主キー | `suppression_id` |
| 主要カラム | **`session_id` FK（必須）**, `point_id` または `candidate_id`, `suppression_kind`, `created_at`, `created_by` |
| JSON | 追加コンテキスト |
| 備考 | **session 内に JSON だけ**でもよいが、**監査・013 からの参照**では **行単位の方が明確**。 |

### 7.14 `artifact_relation`

| 項目 | 内容 |
|------|------|
| 役割 | **lineage**。**rerun** で「旧 `metadata_id` → 新 `metadata_id`」等を記録。 |
| 主キー | `relation_id` |
| 主要カラム | `from_artifact_type`, `from_id`, `to_artifact_type`, `to_id`, `relation_kind`（`SUPERSEDES`／`DERIVED_FROM`／`TRIGGERED_BY_JOB`）, `job_id` FK |
| 備考 | **stale reference 判定**に **世代グラフ**を使う場合に必須に近い。 |

### 7.15 `audit_log`

| 項目 | 内容 |
|------|------|
| 役割 | **API／ジョブ／人確認**の追跡。014 の相関 ID と整合。 |
| 主キー | `audit_id` |
| 主要カラム | `workspace_id`, `actor_id`, `action`, `resource_type`, `resource_id`, `job_id`, `session_id`, `request_id`, `created_at` |
| JSON | `payload_diff`（任意） |

---

## 8. 主要リレーション

### 8.1 カーディナリティ（原則）

| 親 | 子 | 関係 |
|----|-----|------|
| `table_scope` | `normalized_dataset` | **1:N**（世代・rerun） |
| `normalized_dataset` | `analysis_metadata` | **1:1**（同一世代のペア）。**rerun で両方とも新行** |
| `analysis_metadata` | `human_review_session` | **1:N**（再オープン方針次第で **1:1 運用**も可・005 正本） |
| `analysis_metadata` | `confidence_evaluation` | **1:N**（再評価） |
| `analysis_metadata` | `suggestion_set` | **1:N**（複数 run） |
| `human_review_session` | `human_review_answer` | **1:N** |
| `human_review_session` | `suppression_record` | **1:N** |
| `analysis_job` | 各種 artifact | **1:N**（1 ジョブが複数段階で複数 ID を触る） |

### 8.2 必須／任意参照

- **`metadata_id` → `dataset_id`**: **必須**（004 の前提）。
- **`session_id` → `metadata_id`**: **実質必須**（005・014）。
- **`suggestion_set` → `metadata_id`**: **必須**（013 主入力）。**`dataset_id` は任意 FK**（補助）。
- **`evaluation_id` → `metadata_id`**: **強く推奨**（011・014）。

### 8.3 rerun 時の再接続ルール

- **新 `job_id`** を発行し、**新 artifact 行**を挿入。**旧行は `is_latest = false`, `superseded_by = 新 PK`**。
- **`artifact_relation`** に `SUPERSEDES` を記録。
- **API が返す ID** は **最新を既定**とし、**旧 ID 参照は stale**（§10）。

---

## 9. 状態管理と遷移制約

### 9.1 `human_review_session.state`

- **列 `state`** に 006 §6 の enum を **そのまま**格納する。
- **禁止遷移**は **アプリケーション層が主**。**DB では**:
  - **状態テーブル**（`(from_state, to_state)` 許可リスト）＋トリガ、**または**
  - **CHECK は限定的**（例: `CLOSED_UNRESOLVED` 後の更新禁止は **更新トリガ**で実装しやすい）
- **`WAITING_RERUN`** 等は **列で保持**し、**job とのリンク**（`pending_job_id`）を **任意列**で持てる。

### 9.2 answers との整合

- **`human_review_answer` は append 型**を基本とし、**同一 `point_id` の上書き**は **005 のポリシー**に従う（DB では **最新 1 件**ビューまたは `answer_seq`）。

### 9.3 分担

| 層 | 役割 |
|----|------|
| DB | **不変条件**（FK・NOT NULL・一部 CHECK）、**監査行** |
| アプリ | **005 の完全な状態機械** |
| API（014） | **窓口・エラーコード** |

---

## 10. versioning / lineage / rerun 設計

### 10.1 原則

- **成果物行は上書きせず**、**新行挿入 + superseded 鎖**。
- **`artifact_version`** は **単調増加**（テーブル単位または `table_id` 単位で定義）。
- **`is_latest`** は **クエリ最適化用**。**真実は `superseded_by` が null の葉**でもよい。

### 10.2 stale reference

- クライアントが **旧 `metadata_id`** で suggestion を要求した場合、**DB 上その行は `is_latest = false`**。
- API（014）は **409／業務エラー**（012）で **最新 ID を指示**（014 §13 と整合）。

### 10.3 `artifact_relation` の必要性

- **rerun・部分再実行**が増えるほど **必須に近い**。
- **最低限**: `metadata`／`dataset` の **SUPERSEDES** エッジ。

### 10.4 `table_id` を軸とした lineage

- **`table_id` から** `artifact_relation` を辿り、**全世代の metadata／dataset** を復元可能にする **方針**を推奨。

---

## 11. JSON カラム方針

### 11.1 列で持つもの

- **主キー・外部キー**（§6）。
- **`state`, `status`, `kind`, `normalization_status`, `decision`, `decision_recommendation`**（enum は CHECK または lookup）。
- **`is_latest`, `artifact_version`, `superseded_by`, `superseded_at`**。
- **`created_at`, `completed_at`, `answered_at`**。
- **頻繁にフィルタされるスカラー**（`table_id`, `metadata_id`, `session_id`, `evaluation_id`, `suggestion_run_id`）。

### 11.2 JSON で許容するもの

- **`evidence[]` 詳細**, **`trace_map`**, **`review_points` 全文**（サテライト化前）, **`scores` 内部**, **`explanation` ネスト**, **`analysis_candidates` 全文**（サテライト化前）, **`cells` 巨大辞書**。

### 11.3 原則文

- **検索・整合制約・JOIN の核になる識別子と状態は列**とする。**可変・深いツリー・大容量配列は JSON** とし、**006 の意味**を **JSON 内キー**でも変えない（スキーマ検証はアプリまたは DB 拡張で後続）。

---

## 12. index / search / 性能考慮

| 対象 | index 方針 |
|------|------------|
| PK | 全テーブルクラスタ／B-tree |
| FK | **`dataset_id`, `metadata_id`, `table_id`, `session_id`, `job_id`** に **補助 index** |
| latest | **`(table_id, artifact_type, is_latest)`** 部分 index（where `is_latest = true`） |
| ジョブ | **`(workspace_id, status, created_at)`**, **`job_id` の単独** |
| 監査 | **`(created_at)`, `(actor_id, created_at)`** |
| suppression | **`(session_id)`** |

---

## 13. 監査 / 権限 / 論理削除方針

- **物理削除**: 成果物は **原則禁止**。**法的要件**がある場合のみアーカイブテーブルへ移動。
- **論理削除**: `deleted_at` を **テナント境界付き**で持てる（006 に無い場合は **015 拡張**として明示）。
- **権限**: **workspace スコープ**で **行レベル**。**読取／実行／人確認**ロールは 014 §14 と整合。
- **監査**: `audit_log` ＋ **DB 監査トリガ**（任意）。

---

## 14. 014 API との対応

| 014 resource（概念） | DB 主テーブル |
|----------------------|----------------|
| `POST .../table-analysis/jobs` | `analysis_job`（＋`job_stage_run`） |
| `GET .../jobs/{job_id}` | `analysis_job` |
| `GET .../tables/{table_id}` | `table_scope` ＋最新 ref 集約ビュー |
| `GET .../datasets/{dataset_id}` | `normalized_dataset` |
| `GET .../metadata/{metadata_id}` | `analysis_metadata` |
| `GET .../evaluations/{evaluation_ref}` | `confidence_evaluation`（`evaluation_id`） |
| `GET .../suggestion-runs/{suggestion_run_ref}` | `suggestion_set`（`suggestion_run_id`） |
| `GET .../review-sessions/{session_id}` | `human_review_session` |
| `POST .../answers` | `human_review_answer` |
| `GET .../suppression` | `suppression_record` または session 投影 |

---

## 15. 006 との対応

- **各 006 エンティティ**は **§7 のテーブル**に **1:1 対応**させる（`File`／`Sheet` は **`source_id` 系**にマッピングし、本書は **省略または別表**で追記可）。
- **列挙**は **006 §6** を **CHECK 制約または lookup テーブル**へ。
- **006 を無断で変更しない**。差分は **006 改訂後に 015 を追随**する。

---

## 16. 今後拡張

- **DDL 完全版**、**マイグレーション戦略**、**読み取りレプリカ**。
- **`review_point` 正規化テーブル**、**candidate 必須サテライト化**。
- **015 と OpenAPI の列レベル対応表**（014 次版と合わせて 1 ファイル化）。
- **バックアップ・PII マスキング**。

---

## 付録 A. suppression 保管の比較と採用方針（初版）

| 方式 | 長所 | 短所 |
|------|------|------|
| session 行内 JSON のみ | 実装が速い | 監査・部分検索・013 からの参照説明が弱い |
| **`suppression_record` 独立** | **005 正本の行として説明可能**、**監査に強い** | テーブルが増える |

**初版の推奨**: **`suppression_record` を正として持ち**、`human_review_session` には **集約サマリまたは件数**のみ持たせる（任意）。**013 が「抑制済み候補」を返す**ときは **`session_id` 経由で `suppression_record` を参照した結果**である旨を **アプリ層契約**で固定する（005・013 正本と整合）。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-06 | 初版。job／artifact 分離、主要テーブル、参照・世代・014 対応・JSON 方針。 |
| 0.1 追補 | 2026-04-07 | 014 整合: §5.2 に API 用語と 014 §5 への参照を追記。 |
