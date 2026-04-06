---
id: SPEC-TI-014
title: API仕様書
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
---

## 1. 文書情報

| 項目 | 値 |
|------|-----|
| 文書 ID | SPEC-TI-014 |
| 題名 | API 仕様書（表解析パイプライン実装接続） |
| 版 | 0.1 |
| 状態 | Draft |
| 最終更新 | 2026-04-07 |

本版は **実装接続フェーズの概念版** である。OpenAPI 3 の完全定義、全エンドポイントの request/response JSON Schema、認証スキームの細目は **本書の次版またはリポジトリ内 OpenAPI アーティファクト**で確定する。

---

## 2. 目的と適用範囲

### 2.1 目的

本仕様書は、表解析コア仕様群（001〜005、011、013）および **データ契約（006）** を、**外部／内部から呼び出し可能にする API 契約**として束ねる。**ロジック本文の再定義は行わない**。

一言で表すと、本書は **「表解析パイプラインを、責務境界を壊さずに呼び出し可能にする契約仕様書」** である。

### 2.2 対象範囲

- **実行 API**: ジョブ／ランの開始、再実行、ステータス照会、非同期完了通知に相当する契約（具体プロトコルは実装選択だが、契約上の義務を定義する）。
- **成果物参照 API**: 006 に定義されたエンティティ相当の取得・一覧。
- **人確認 API**: 005 の状態機械と `HumanReviewSession` を **窓口として実行する**ための操作。
- **候補取得 API**: 013 の `SuggestionSet` および関連参照の取得、011 の評価結果参照との接続。

### 2.3 非対象範囲

- 表読取アルゴリズム（001）、判定ルール本文（002）、正規化ルール本文（003）、分析メタの意味定義（004）、人確認の業務判断ルール（005）、信頼度算出式（011）、候補生成アルゴリズム（013）。
- **物理 DB スキーマ、マイグレーション、インデックス**（015）。
- **画面文言、コンポーネント配置**（007）。

### 2.4 既存仕様との責務境界

| 仕様 | 本書との関係 |
|------|----------------|
| 001 | 観測結果の意味・`TableReadArtifact` の生成規則の正本。API は成果物 ID で参照するのみ。 |
| 002 | `decision`（Judgment）の正本。API は取得・再実行トリガにとどめる。 |
| 003 | `NormalizedDataset`・`dataset_id` の正本。 |
| 004 | `AnalysisMetadata`・`metadata_id`・`review_points` の正本。 |
| 005 | `HumanReviewSession`・suppression・状態遷移の正本。API は **005 を上書きしない窓口**である。 |
| 006 | **DTO／フィールド意味の正本**。API の I/O は 006 に準拠し、本書は **投影と振る舞い**を定義する。 |
| 011 | `ConfidenceEvaluation`・`decision_recommendation`・説明構造の正本。 |
| 012 | エラーコードと意味の正本。API のエラー表現は 012 と整合する。 |
| 013 | `SuggestionSet`・候補構造の正本。 |
| 015 | **永続化・テーブル粒度の正本**。本書は **DB 物理形を定義しない**（**015**）。 |

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
| SPEC-TI-015 | [DB 設計仕様書](./SPEC-TI-015-db-design.md)（永続化側の受け先） |

---

## 4. API 設計原則

### 4.1 リソース指向

- URL／操作名は **ジョブ**、**テーブル**、**成果物**（dataset / metadata / session / evaluation / suggestion run）を主語に据える。
- 実装は REST、RPC、GraphQL のいずれでもよいが、**本書が定義する識別子と参照関係**を損なわないこと。

### 4.2 実行系と参照系の分離

- **実行系（コマンド）**: 副作用を伴う処理の開始。レスポンスは **`job_id`（または `run_id`）** と、生成が確定した場合は **参照 ID 群**を返すことを基本とする。
- **参照系（クエリ）**: 成果物本体またはサマリの取得。GET 相当の **冪等**操作とする。

### 4.3 同期と非同期

- パイプライン全体は **非同期実行が既定**とする。長大な `TableReadArtifact` やパイプライン遅延に対応するため、**受理レスポンスは速く、本体は GET で再取得**する。
- 短い検証のみ同期を許容してよい（実装方針）。その場合も **契約上の ID** は 006 に従う。

### 4.4 バージョニング

- API バージョンは **URL プレフィックス**（例: `/v1/table-analysis/...`）または **ヘッダ**で表現する。破壊的変更時はメジャーを上げる。
- **006 の `schema_version`**（データ契約）とは別軸であるが、**レスポンスにデータ契約版を含めうる**（006 の `schema_version` フィールドの投影）。

### 4.5 冪等性

- 同一 **`idempotency_key`**（クライアント生成の一意キー）による **同一意味のジョブ POST** は、サーバが **同一論理結果**を返すか、**既存ジョブを指す**ことを目標とする（HTTP の詳細は実装で 012 と整合）。
- **人確認の回答投稿**は、**`answer_id` または idempotency** で二重送信を吸収しうる（005・014 の次版で確定）。

### 4.6 トレーサビリティ

- リクエストに **相関 ID**（例: `X-Request-Id`）を受け付け、レスポンス・監査ログに引き写す。
- **`job_id` → `table_id` → `dataset_id` / `metadata_id` / `session_id` / `evaluation_ref` / `suggestion_run_ref`** の鎖が追跡可能であること（015 で永続化する前提）。

### 4.7 006 準拠原則

- **フィールド名・列挙・意味**は **006 を正本**とする。本書は **必須／任意の API 上の扱い**、**取得単位**、**エラー時の欠損**を定義する。
- 006 に無い DTO を API だけで増やす場合は **006 改訂または本書の明示的拡張**として記録する（本版では新規 DTO を増やさない）。

---

## 5. 識別子と参照契約

### 5.1 中心語彙（006 との対応）

| ID / ref | 役割 | 正本・備考 |
|----------|------|------------|
| `table_id` | 001 の観測対象テーブル、002〜013 の参照アンカー | 006 `TableCandidate` 系 |
| `dataset_id` | 003 の正規化主成果物 | 006 `NormalizedDataset` |
| `metadata_id` | 004 の分析メタ主成果物 | 006 `AnalysisMetadata` |
| `session_id` | 005 の `HumanReviewSession` | 006 §5.9 |
| `evaluation_ref` | 011 の `ConfidenceEvaluation.evaluation_id` と同一キー空間 | 006 §5.10、§5.12 `JobRun` |
| `suggestion_run_ref` | 013 の `SuggestionSet.suggestion_run_id` と同一キー空間 | 006 §5.11、§5.12 `JobRun` |
| `job_id` | 006 `JobRun.job_id` に相当する実行単位 | 006 §5.12 |
| `artifact_version` | 同一論理成果物の再生成版を区別する（**オプション**） | Phase 4／015 で確定 |
| `idempotency_key` | クライアント指定の冪等キー | 本書 §4.5 |
| `document_id` / `source_id` | アップロード原本・ファイル束ね（**テナント配下**） | 014／015 で命名確定 |

#### 5.1.1 API 名と DB 主キー列名（015 との対応）

本書および 006 の **`evaluation_ref` / `suggestion_run_ref`**（**`JobRun` 上の参照**）は、**011／013 成果物の ID と同一キー空間**である。**永続化時の主キー列名**は **015 §5.2** に従い、**`evaluation_id` / `suggestion_run_id`** とする（**値は同一**）。**レスポンス JSON** は **006 のフィールド名**を優先し、**パス・ジョブ応答**では **`evaluation_ref` 等の API 慣用名**を用いてよい。

### 5.2 相互参照ルール（契約上の原則）

- **`metadata_id` は `dataset_id` に従属**する（004 は正規化済みを前提）。API は `metadata` 取得時に **`dataset_id` を返してよい**。
- **`session_id` は `table_id` および通常は `metadata_id` と関連**する。005 正本の発生条件に従う。
- **`evaluation_ref` は `table_id` に紐づき**、**`metadata_id` ないし `dataset_id` と一緒に辿れる**ことが望ましい（結合の物理形は 015）。
- **`suggestion_run_ref` は主入力 `metadata_id` に依存**しうる。013 は **004 を主入力**とし、**011・005 を読む側**である（本書はその前提でレスポンスを設計する）。

### 5.3 null 許容・未生成状態

- パイプライン途中では **`dataset_id` 未確定**などがありうる。実行 API の **ジョブ状態**に応じて **参照 GET は 404 または 012 の「未準備」コード**で応答する（詳細は §13）。
- **`evaluation_ref` / `suggestion_run_ref` は `JobRun` 上任意**。ジョブ種別・成功時のみ付与されうる（006）。

### 5.4 `decision` と `decision_recommendation` の分離（API 上の必須区別）

- **`decision`**: 002 の **Judgment** 結果。レスポンス・リソースで **`decision`（Judgment）** としてラベルする。
- **`decision_recommendation`**: 011 の **推奨**。**002 を上書きしない**。API ドキュメントで **同一綴りでも別フィールド**として記載する。

---

## 6. ライフサイクル概要

1. **表解析ジョブ開始**: 原本提出 → `job_id` 発行 → 非同期で 001→002→003→004 を実行。
2. **判定・正規化・メタ生成**: 各段階完了時に **参照 ID** が確定し、ジョブ詳細またはサブリソースに露出。
3. **review session 発生**: 004 の `review_required` / `review_points` に基づき **005 が `session_id` を生成**（条件は 005 正本）。
4. **confidence evaluation**: 011 が実行され **`evaluation_ref` が付与**されうる（ポリシーは 011／製品）。
5. **suggestion generation**: 013 が **`metadata_id` を主入力**に実行され **`suggestion_run_ref` が付与**されうる。
6. **rerun / 再評価**: 005 経由の再実行要求または実行 API の **段階指定 rerun**。**新 `job_id` ないし新 `artifact_version`** が発生しうる（§12）。

---

## 7. 共通 I/O 契約

### 7.1 リクエスト

- **認証**: Bearer 等（詳細はセキュリティ章）。**テナント／ワークスペース**は 006 の `workspace_id` 概念と整合するヘッダまたはパスで表現しうる。
- **`Idempotency-Key`**: 実行系 POST で推奨。
- **`X-Request-Id`**: 任意。サーバは欠損時に生成してよい。

### 7.2 レスポンスエンベロープ（概念）

- **成功**: ボディは **006 準拠の JSON** または **ジョブサマリオブジェクト**（`job_id`, `status`, 確定済み ref の部分集合）。
- **エラー**: **012 準拠のコード**を含むオブジェクト（`error_code`, `message`, `details`）。HTTP ステータスとの対応表は **014 次版または OpenAPI**で固定。

### 7.3 ページネーション・フィルタ

- 一覧 API は **`cursor` または `page`+`limit`** をサポートしうる。デフォルト上限を定める。
- **`table_id`, `metadata_id`, `session_id`** によるフィルタを候補一覧等で許容。

### 7.4 日時形式

- **RFC 3339**（UTC 推奨）を既定とする。

### 7.5 列挙

- **006 §6** の列挙をそのまま転記せず、**API レスポンスでは 006 の値**を返す。

---

## 8. 実行 API

**主語は `job` / `run`。** 以下のパスは **論理リソース**の例である（実装でプレフィックスを調整してよい）。

| 操作（概念） | メソッド・パス（例） | 概要 |
|--------------|---------------------|------|
| 表解析ジョブ開始 | `POST /v1/table-analysis/jobs` | 原本参照を受け取り `job_id` を返す。受理後、非同期でパイプライン実行。 |
| ジョブ状態取得 | `GET /v1/table-analysis/jobs/{job_id}` | `status`, 確定した `table_id`, `dataset_id`, `metadata_id`, `evaluation_ref`, `suggestion_run_ref` の部分集合。 |
| 単一段階 rerun | `POST /v1/table-analysis/jobs/{job_id}/rerun` | 001〜004 のうち **指定段階から**再実行（ペイロードで段階指定。詳細は次版）。 |
| review 後 rerun | `POST /v1/review-sessions/{session_id}/rerun` または上記の派生 | **005 正本の遷移**に従い、再パイプラインを起動。 |
| suggestion run 開始 | `POST /v1/suggestion-runs` | **主入力 `metadata_id`**。受理後 `suggestion_run_ref` を返す。 |

**POST 受理レスポンスの基本形（概念）**: `job_id`, `status`（例: `PENDING`）, 既知なら `table_id`。**本体は GET で再取得**（**§4.2** の実行系／参照系分離）。

---

## 9. 成果物参照 API

| 操作（概念） | パス（例） | 返却（006 準拠） |
|--------------|------------|------------------|
| テーブルサマリ | `GET /v1/tables/{table_id}` | `table_id`, 関連 `job_id`, 主要 ref のインデックス |
| TableReadArtifact | `GET /v1/tables/{table_id}/read-artifact` | 006 `TableReadArtifact`（大ペイロードは **フィールド選択**または別メディア URL を次版で） |
| Judgment / evidence | `GET /v1/tables/{table_id}/decision` | 006 `JudgmentResult`（`decision` は 002 正本） |
| NormalizedDataset | `GET /v1/datasets/{dataset_id}` | 006 `NormalizedDataset` |
| AnalysisMetadata | `GET /v1/metadata/{metadata_id}` | 006 `AnalysisMetadata`（`review_points` を含みうる） |
| ConfidenceEvaluation | `GET /v1/evaluations/{evaluation_ref}` | 006 `ConfidenceEvaluation` |
| SuggestionSet | `GET /v1/suggestion-runs/{suggestion_run_ref}` または `GET /v1/suggestions/{suggestion_run_ref}` | 006 `SuggestionSet` |
| 関連成果物一覧 | `GET /v1/tables/{table_id}/artifacts` | ref の一覧（015 の lineage 投影の前提） |

---

## 10. 人確認 API

**API は 005 の状態遷移を実行する窓口**である。**遷移の可否の正本は 005**（006 §6 禁止遷移下書きを含む）。

| 操作（概念） | パス（例） | 概要 |
|--------------|------------|------|
| review session 作成 | `POST /v1/review-sessions` | `metadata_id` 等を受け、005 に従い `session_id` を発行。 |
| session 取得 | `GET /v1/review-sessions/{session_id}` | 006 `HumanReviewSession`。 |
| review_points 取得 | `GET /v1/metadata/{metadata_id}/review-points` または session 配下 | 004 正本の投影。 |
| answers 登録 | `POST /v1/review-sessions/{session_id}/answers` | 006 `answers[]` 要素に準拠。 |
| state 遷移 | `PATCH /v1/review-sessions/{session_id}` または専用サブリソース | 005 が許可する遷移のみ。 |
| rerun 要求 | `POST /v1/review-sessions/{session_id}/rerun` | パイプライン再実行トリガ。 |
| suppression 結果参照 | `GET /v1/review-sessions/{session_id}/suppression` | **suppression の正本は 005**。013 が返す抑制済み候補の根拠説明にこの参照を紐づけうる。 |

---

## 11. 候補取得 API

**013 は候補生成の実行者。suppression の正本は 005。recommendation の正本は 011。**

| 操作（概念） | パス（例） | 概要 |
|--------------|------------|------|
| 候補一覧 | `GET /v1/suggestion-runs/{suggestion_run_ref}/candidates` | 006 `analysis_candidates[]` の投影。 |
| suppression 適用後候補 | 同上＋クエリ `suppression=applied` 等 | **005 の suppression 状態を読んだ結果**である旨をレスポンスメタまたはドキュメントで明記。 |
| recommendation 付き候補 | `metadata_id` または `evaluation_ref` と結合した取得 | **`decision_recommendation` は 011 由来**で **`decision`（002）と混在表示しない**。 |
| explanation / provenance | `GET /v1/evaluations/{evaluation_ref}` または候補内 `evidence` | 011 の `explanation`・006 `TraceRef` 方針に従う。 |

**主入力の原則**: 候補生成の **API 契約上の主キーは `metadata_id`**。`dataset_id` は **補助参照**。`evaluation_ref`・`session_id` は **013 が読む外部コンテキスト**。

---

## 12. 状態遷移と整合制約

### 12.1 HumanReviewSession

- **許可遷移**: 006 §6 暫定 enum と **禁止遷移下書き**に従う。API は **禁止遷移に対して 409 相当**（012 の conflict 系）を返しうる。
- **005 の更新**が正本。API レイヤは **バリデーションの窓口**にすぎない。

### 12.2 rerun 後の参照整合

- rerun により **新 `dataset_id` / `metadata_id`** が発行されうる。クライアントは **`job_id` または `artifact_version`** で **最新 ref を再取得**する責務を持つ（契約上の推奨）。

### 12.3 artifact versioning

- **同一 `table_id` に複数バージョン**が共存しうる。GET は **明示版指定**または **「最新」解決規則**をクエリで表す（次版で確定）。

### 12.4 stale reference

- 古い `metadata_id` で候補生成を要求した場合、**409 または業務エラー**（012）で **再取得を促す**（§13）。

---

## 13. エラー / 異常系

本書は **012 のコード体系**に合わせる。以下は **API 契約で頻出するカテゴリ**である。

| カテゴリ | 意味 | 例示的な条件 |
|----------|------|----------------|
| validation error | 入力不備 | 必須 ID 欠落、無効 enum |
| not found | リソース不存在 | 未知の `dataset_id` |
| conflict | 状態不整合 | 禁止 state 遷移、同時更新 |
| invalid state transition | 005 違反 | `RESOLVED` 後の不正操作 |
| stale reference | 版ずれ | 旧 `metadata_id` での suggestion 実行 |
| rerun required | 再実行が必要 | 中間成果が無効化された後の参照 |
| suppression blocked | 抑制により操作不可 | 005／013 組合せのポリシー |

HTTP ステータスと `error_code` の対応は **OpenAPI 化時に固定**する。

---

## 14. セキュリティ / 権限制御 / 監査

### 14.1 権限（概念ロール）

- **読取**: 成果物 GET、ジョブ状態参照。
- **実行**: ジョブ POST、rerun、suggestion run 開始。
- **人確認**: session 操作、answers 投稿、suppression 関連。

### 14.2 監査

- **誰が** `answers` を投稿したか（`answered_by`）、**いつ**かは 006 に従い **保持・返却**する。
- **API 層**は **監査ログに `job_id`, `session_id`, 相関 ID** を記録する（015 の監査テーブルと整合）。

### 14.3 データ分離

- **テナント／ワークスペース**を跨ぐ ID 推測を **404 でマスク**するなど、**列挙攻撃対策**を実装指針とする（詳細は次版）。

---

## 15. 006 / 015 への接続注記

### 15.1 006

- **型・列挙・フィールド意味**は **006 を優先**する。本書は **エンドポイントと振る舞い**を定義し、**JSON Schema の正本は 006 Phase 4 拡張**に委ねる。

### 15.2 015

- **ジョブ系**（**`analysis_job`**／`job_stage_run` 等、**015 §7**）と **成果物系**（`normalized_dataset`, `analysis_metadata`, `human_review_session`, `confidence_evaluation`, `suggestion_set` 等）を **分離**しやすいよう、本書のリソース粒度を揃えた。
- **API リソース ≒ 015 の主要エンティティ候補**（`artifact_relation` / lineage は 015 で詳細化）。

### 15.3 API と DB の責務差分

- **API** は **同期境界・認可・エラー表現**を担う。**DB** は **永続化・整合制約・履歴**を担う。同一フィールドでも **API 名と列名は一致しない**ことがある（**`evaluation_ref` ↔ `evaluation_id` 等は 015 §5.2**）。

---

## 16. 今後拡張

- **OpenAPI 3 完全版**、Webhook／SSE によるジョブ完了通知。
- **部分取得**（JSON Patch、GraphQL フィールド選択）による大成果物の最適化。
- **SPEC-TI-015** との **列レベル対応表**（エンドポイント × DTO × テーブル）。
- **016+**（運用、バッチ、外部コネクタ）との接続は本書の上に別層で定義する。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-06 | 初版。実装接続フェーズの API 契約（原則・識別子・ライフサイクル・論理リソース・エラー・015 接続注記）。 |
| 0.1 追補 | 2026-04-07 | 015 整合: §2.4 に 015 行、§5.1.1 API／DB 列名対応、§15.2 ジョブ系表記、`evaluation_ref` 対応注記。 |
