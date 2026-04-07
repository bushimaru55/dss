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
| 最終更新 | 2026-04-03 |

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
- **エラー**: **012 準拠のコード**を含むオブジェクト。Table Intelligence の **`/api/v1/*`** では **`error_code` + `detail`（+ `errors`）**（OpenAPI 0.1.3 `ErrorResponse`）。`message` / `details` / `request_id` は Phase 4 で拡張しうる。
- **HTTP ステータス（OpenAPI 0.1.4）**: 主要 operation ごとに **400 / 401 / 404** を path に列挙。**workspace 越境・存在しない ID は 404 マスク**（§14.3）。**403**（`TI_PERMISSION_DENIED`）は components に定義するが **MVP では未認証が主に 401** のため **全 path には列挙しない**。**409** は stale / 競合の **将来枠**—一部 path のみ記載し **MVP では多く未使用**。
- **Review answers I/O（OpenAPI 0.1.5）**: `POST .../answers` の **正しい request** は **`TiMvpSubmitReviewAnswersRequest`**。006 の `point_id` / `client_nonce` 等は **未使用**（Phase 4 **additive**）。
- **409（OpenAPI 0.1.6 / §13.1）**: 操作別の **意図・分類（A/B/C/D）** と **path 上の 409 の有無**を固定。**MVP 実装は 409 を広く返さない**。
- **401（OpenAPI 0.1.7）**: **OpenAPI に載るすべての operation** で **`401 Unauthorized`** を path に列挙。[GUIDE-TI-table-intelligence-api-errors.md](./GUIDE-TI-table-intelligence-api-errors.md) と一致。
- **409（OpenAPI 0.1.8）**: **`POST /suggestion-runs`** の **superseded metadata** のみ **実装**。レスポンスは **`TI_CONFLICT`**（`exception_handler`）。

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

**MVP 実装注記**: 同一 `Idempotency-Key` の再送は **HTTP 200**、新規受理は **202** としうる（詳細は **§16**、OpenAPI `TiMvpJobSummary`）。

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

**MVP 実装注記（`GET .../tables/{table_id}/read-artifact`）**: 応答は **`table_read_artifact`（015 §7.4）の `is_latest` 行**から組み立てる。MVP パイプライン `materialize` が **`TableScope` 直後**に **001 本格エンジン前のスタブ**（稀疏 `cells`・`R{row}C{col}` 形式に寄せた最小キー、`merges`/`parse_warnings` は空配列から開始）を INSERT する。**行が無い場合は 404**（§14.3 の **404 マスク**に従う）。**rerun** 後は旧 `table_id` 側の latest が外れうるため、旧 URL は **404** になりうる（新 `table_id` の GET が正）。

**MVP 実装注記（`GET .../tables/{table_id}/decision`）**: 応答は **`judgment_result`（015 §7.5）の `is_latest` 行**から組み立てる。MVP パイプライン `materialize` が **002 本格エンジン前のスタブ行**を INSERT する。**行が無い場合は 404**（テーブル不存在・workspace 越境は §14.3 の **404 マスク**に従い区別しない）。`taxonomy_code` は **`TI_TABLE_UNKNOWN`** を既定とし、011 の `decision_recommendation` は **本レスポンスに含めない**（`/evaluations/...` 側）。

---

## 10. 人確認 API

**API は 005 の状態遷移を実行する窓口**である。**遷移の可否の正本は 005**（006 §6 禁止遷移下書きを含む）。

| 操作（概念） | パス（例） | 概要 |
|--------------|------------|------|
| review session 作成 | `POST /v1/review-sessions` | `metadata_id` 等を受け、005 に従い `session_id` を発行。 |
| session 取得 | `GET /v1/review-sessions/{session_id}` | 006 `HumanReviewSession`。 |
| review_points 取得 | `GET /v1/metadata/{metadata_id}/review-points` または session 配下 | 004 正本の投影。 |
| answers 登録 | `POST /v1/review-sessions/{session_id}/answers` | **MVP 事実**: OpenAPI **`TiMvpSubmitReviewAnswersRequest`**（`answers[]`: `question_key` + `answer_value` 任意 JSON、任意 `mark_resolved` / `resolution_grade`）。006 `ReviewAnswer` 完全形は **Phase 4 additive**。 |
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

**利用者向けの HTTP ステータス早見**（非エンジニア可読の 1 ページ）は [GUIDE-TI-table-intelligence-api-errors.md](./GUIDE-TI-table-intelligence-api-errors.md) を参照。

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

HTTP ステータスと `error_code` の対応は **OpenAPI 化時に固定**する。**409 の操作別の意図と MVP 実装差**は **§13.1** を正とする。

### 13.1 `409 Conflict` 実装マトリクス（MVP と将来）

**境界（再掲）**

- **404 マスク**: テナント越境・無権限の「存在はするが見せない」は **常に 404**（§14.3）。**409 に昇格しない**。
- **400**: リクエスト構文・**同一 workspace 内で検証可能な参照不整合**（例: `dataset_id` が当該 `metadata_id` と不一致）は **クライアント誤り**として **400**（MVP 実装: `POST /suggestion-runs` の `ValidationError`）。
- **409**: **意味のある競合**のみ—**サーバの現在状態とリクエストの意図が両立しない**が、**再取得・別操作で解消しうる**とき。無闇に増やさない。

**分類凡例**: **A**＝今すぐ 409 実装を優先しうる / **B**＝OpenAPI・本節に将来枠として残す（現状未返却） / **C**＝400 または 404 で足りる / **D**＝ポリシー・設計決定が先（HTTP だけでは決めない）。

| Operation | 409 候補条件（例） | 分類 | メモ |
|-----------|-------------------|------|------|
| `POST /table-analysis/jobs` | 冪等キー競合で「別内容の POST」 | **D** | 現状は **200/202 で既存 job を返す**方針。真の競合検知は **Idempotency-Key + ボディハッシュ**等の設計が先。 |
| `POST /table-analysis/jobs` | ジョブ同時二重受理 | **D** | キュー・DB 制約レベルの論点。**409 より 202 重複受理の許容**もありうる。 |
| `POST .../jobs/{job_id}/rerun` | 元ジョブが superseded / 再実行禁止状態 | **B** | **015 §10** lineage 充実後に「古い `job_id` からの rerun」を拒否するなら 409 候補。MVP は **常に新 job 作成**。 |
| `POST .../jobs/{job_id}/rerun` | パイプライン実行中の再 rerun | **B** | **「進行中は拒否」**を入れるなら 409。未導入なら **D**（許可するかどうかの製品判断）。 |
| `POST /review-sessions` | 同一 `metadata_id` にアクティブ session 既存 | **D** | MVP は **毎回新規作成**。一意制約・「開いている session は 1 つ」なら将来 **409** ありうる。 |
| `POST .../review-sessions/{id}/answers` | 005 **禁止遷移**（例: 終端 state への回答） | **B** | §12.1・§13 表の **invalid state transition**。**楽観ロック**（`If-Match` / `updated_at`）なら同一分類。MVP は **状態ガード未実装**。 |
| `POST .../review-sessions/{id}/answers` | 同一 `question_key` の上書き禁止ポリシー | **D** | 005 / 015 §9.2 の **append vs 最新 1 件**の正本決定後。 |
| `POST .../review-sessions/{id}/rerun` | 既に **WAITING_RERUN** 等で再実行待ち | **B** | 二重パイプライン起動を嫌うなら 409。MVP は **検知せず 202**。 |
| `POST .../review-sessions/{id}/rerun` | state が rerun 不適格 | **B** | 005 許可遷移との組合せ。 |
| `POST /suggestion-runs` | **`metadata_id` が lineage 上 stale**（`artifact_relation` の metadata **旧→新** SUPERSEDES） | **A** | **実装済（MVP）**: `TI_JOB_RERUN_SUPERSEDES` / `TI_REVIEW_RERUN_SUPERSEDES` の **from** が当該 ID なら **409** + `TI_CONFLICT`。**`is_latest` 列は未使用**。 |
| `POST /suggestion-runs` | `dataset_id` / `evaluation_ref` / `session_id` が metadata と不整合 | **C** | 実装は **400**（`ValidationError`）。**404 にしない**（リソースは存在するが組合せが悪い）。 |
| `GET .../suggestion-runs/{ref}/candidates` | stale / 競合 | **C** | **読取は 200 で保存済み候補を返す**が自然。ref 自体が無効・越境は **404**。**GET に 409 は付けない**（OpenAPI 0.1.6 で削除）。 |

**MVP 実装（table_intelligence）の事実**: **`POST /suggestion-runs`** のみ **superseded metadata** で **`HTTP 409`**（`TI_CONFLICT`）。他 operation は **現状 409 未使用**（answers / review rerun は将来枠）。`exception_handler` は **409** に `TI_CONFLICT` を付与。

**OpenAPI（0.1.6 以降）**: **`POST .../answers`**・**`POST .../review-sessions/.../rerun`** に **将来枠として 409** を残す。**`POST /suggestion-runs`** の **409 は stale metadata 実装と一致**（**0.1.8**）。**`GET .../candidates`** から **409 を削除**（実装・§12.4 と整合）。

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

## 16. MVP バックエンド実装との契約差分（整理）

本節は **Table Intelligence Django API（MVP）** と、本書・OpenAPI ドラフトの **意図した完全契約（006 準拠 Phase 4）** の差を固定する。
**正の優先順位**: 運用上は **リポジトリ内 OpenAPI `table-intelligence-openapi-draft.yaml` の 0.1.8 以降**（0.1.3 エンベロープ〜0.1.7 までの内容に加え、**0.1.8: `POST /suggestion-runs` の stale metadata 409**）を **MVP 実装の事実契約**とみなし、本書 §4〜§9 は **原則・識別子・責務**の正本とする。

### 16.1 ジョブ実行系

| 項目 | 完全契約（目標） | MVP 実装（現状） | どちらを正にするか（本ラウンド） |
|------|------------------|------------------|----------------------------------|
| `POST /table-analysis/jobs` 成功ステータス | 非同期受理 **202** のみ記載されていた | 新規 **202**、同一 `Idempotency-Key` 再送は **200** | **実装を正**（OpenAPI を 200/202 に更新済） |
| 冪等キー | ヘッダ推奨（§7.1） | ヘッダ `Idempotency-Key`（ボディは未使用） | **実装を正** |
| 受理レスポンス形 | `JobAcceptedResponse`（`job_id`, `status`, 任意 `table_id`） | `TiMvpJobSummary` 相当（`workspace_id`, `current_stage`, `artifact_refs` 等） | **実装を正**（OpenAPI に `TiMvpJobSummary` 追記） |
| `JobRun.kind` / `table_id` トップレベル | 006 想定 | DB 列・レスポンスとも **未搭載**。ref は **`artifact_refs` 束** | **仕様側を Phase 4 保留**（OpenAPI `JobSummary` の `kind` 必須を緩和） |
| `GET /jobs/{id}` の ref | トップレベル `evaluation_ref` 等もありうる | **詳細も `artifact_refs` に集約**、かつ `request_payload`・`idempotency_key` 露出 | **実装を正**（GET は `TiMvpJobDetail`） |
| `POST .../jobs/{id}/rerun` | OpenAPI は **202** | **201 Created** + `TiMvpJobSummary` | **実装を正**（REST のリソース作成に合わせ OpenAPI を 201） |
| `POST .../review-sessions/{id}/rerun` | **202** | **202**（一致） | 維持 |

### 16.2 人確認・抑制

| 項目 | 完全契約（目標） | MVP 実装（現状） | どちらを正にするか |
|------|------------------|------------------|---------------------|
| `GET .../suppression` | `SuppressionStateResponse`（`session_id` + `records`）想定 | **`SuppressionRecord` の JSON 配列**を直接返却 | **実装を正**（OpenAPI を配列スキーマに変更。将来ラッパへ移行可） |
| `HumanReviewSession` GET | 006 形（`table_id`, `pending_questions` 等） | **`metadata_id` + snapshot 列**中心、`table_id` は返さない | **実装を正**（OpenAPI を MVP 投影に合わせ記述） |
| `POST .../answers` body | 006 `answers[]` 完全形想定 | **`TiMvpSubmitReviewAnswersRequest`**（`question_key` / `answer_value` + 任意 `mark_resolved` / `resolution_grade`） | **実装を正**（OpenAPI 0.1.5 で request を `TiMvp*` 化） |
| `POST .../answers` 戻り | 次版 TODO | `{ "session", "answers" }` | **実装を正**（OpenAPI `TiMvpSubmitReviewAnswersResponse` + `TiMvpHumanReviewAnswer`） |

### 16.3 評価・候補

| 項目 | 完全契約（目標） | MVP 実装（現状） | どちらを正にするか |
|------|------------------|------------------|---------------------|
| `GET /evaluations/{evaluation_ref}` | 006 `ConfidenceEvaluation`（`scores`, `explanation`, `table_id`） | **`evaluation_ref`, `metadata_id`, `confidence_score`, `risk_signals`, `decision_recommendation`（JSON object）** | **実装を正**（011 の `decision_recommendation` はオブジェクトでも可と明記） |
| `GET .../suggestion-runs/{ref}` の `table_id` | 非 null string 想定 | **未バインド時は空文字列 `""`** | **実装を正**（クライアントは `metadata_id` を主キーとする） |

### 16.4 エラー表現

| 項目 | 完全契約（目標） | MVP 実装（現状） | どちらを正にするか |
|------|------------------|------------------|---------------------|
| ボディ | 012 の `error_code` + `message` + `details` | **`/api/v1/*`**: `error_code` + `detail`（+ 任意 `errors`）にラップ済み（P4-1）。**他 `/api/*`**: DRF 既定 | **Ti エンベロープを正**（OpenAPI 0.1.3+ `ErrorResponse`）。主要 path の **HTTP ステータス列挙は 0.1.4**（§18.6）。`message` / `request_id` は Phase 4 **additive** |

### 16.5 ワークスペース・404

- 未知の `workspace_id` は **404 でマスク**（§14.3）。実装と一致。**正: 仕様・実装とも維持**。

---

## 17. 今後拡張

- **OpenAPI 3 完全版**、Webhook／SSE によるジョブ完了通知。
- **部分取得**（JSON Patch、GraphQL フィールド選択）による大成果物の最適化。
- **SPEC-TI-015** との **列レベル対応表**（エンドポイント × DTO × テーブル）。
- **016+**（運用、バッチ、外部コネクタ）との接続は本書の上に別層で定義する。

---

## 18. OpenAPI 0.1.8-draft 利用者向けガイドと Phase 4 移行計画

本節は **クライアント実装者**向けである。OpenAPI **`document_version: 0.1.8-draft`**（`info.version: 0.1.8-draft`）を前提にする。**0.1.3〜0.1.7** の内容は **そのまま下位互換として含まれる**。**0.1.8** では **`POST /suggestion-runs`** の **409（superseded metadata）** を実装・記述と一致。

### 18.1 文書間の役割（再掲）

| 層 | 正本の役割 |
|----|------------|
| **本書 §4〜5・§14** | 原則・識別子・責務境界・404 マスク（変更容易度は低い） |
| **OpenAPI 0.1.8** | MVP の **機械可読な事実契約**（0.1.7 まで＋**`POST /suggestion-runs` の stale metadata 409**） |
| **006（Phase 4）** | **DTO・列挙・JSON 形の最終正本**（API レスポンスはここに収斂させる） |
| **015** | 永続化・lineage；API フィールド名と列名の差は §5.1.1 |

### 18.2 利用上の注意（迷いどころ）

1. **`TiMvp*` を優先**  
   Jobs の受理・詳細、review の suppression GET、answers POST の戻りは **`TiMvpJobSummary` / `TiMvpJobDetail` / `TiMvpSuppressionRecord[]` / `TiMvpSubmitReviewAnswersResponse`** で読む。同名の `JobSummary` / `JobDetail`（006 理想形）は **Phase 4 まで参照用**。
2. **`GET /datasets/{id}` / `GET /metadata/{id}` / `GET /evaluations/{ref}` / `GET /review-sessions/{id}`（および session POST 201）**  
   OpenAPI **0.1.2** では上記の **200/201 レスポンスが `TiMvpNormalizedDataset` 等に明示的に紐付く**。`NormalizedDataset` / `AnalysisMetadata` / `ConfidenceEvaluation` / `HumanReviewSession`（無印）は **006 Phase 4 目標形**として components に残り、生成クライアントは **path ごとの `TiMvp*` を採用**すれば実装と一致する。
3. **`POST /table-analysis/jobs` のステータス**  
   新規 **202**、冪等再送 **200**。**Location ヘッダは付けない**前提（`job_id` はボディ）。
4. **冪等**  
   **`Idempotency-Key` ヘッダ**を正とする。ボディ `idempotency_key` は OpenAPI 上 **deprecated**。
5. **エラー（`/api/v1/*`）**  
   **`error_code` + `detail`**（+ 検証時 `errors`）。未認証は多く **401**（`TI_AUTHENTICATION_REQUIRED`）。**403**（`TI_PERMISSION_DENIED`）は DRF 設定によりありうるが **OpenAPI では全 path に列挙せず** components のみ維持（実装と乖離しすぎないため）。**404** は不存在と **workspace 越境のマスク**の両方に使う（§14.3）。**409** の **path 別の意図**は **§13.1**—MVP では **主に未返却**。**他 `/api/*`** は DRF 既定のまま（エンベロープなし）。
6. **`HumanReviewSession.state`**  
   OpenAPI の enum は 006 草案より **広い**。サーバが返す値は **実装の部分集合**であり、**未知の値はフォールバック表示**で扱う（前方互換）。
7. **Suggestion の主キー**  
   **`metadata_id` を主アンカー**とする。`table_id` が **空文字**のときあり（未バインド）。

### 18.3 エンドポイント別：利用観点レビュー

#### Jobs

| 操作 | クライアントがすべきこと |
|------|-------------------------|
| `POST /table-analysis/jobs` | `workspace_id` 必須。`Idempotency-Key` 推奨。**200 と 202 の両方**で `job_id` を取得し、ポーリングは `GET .../jobs/{job_id}` へ。 |
| `GET .../jobs/{job_id}` | `status` と **`artifact_refs`**（null あり）で完了判定。詳細は `request_payload.mvp_pipeline` も参照しうるが **正は `artifact_refs`**（確定後）。 |
| `POST .../jobs/{id}/rerun` | **201**。新 `job_id` で再度ポーリング。`request_payload.lineage` はサーバマージ（クライアントは通常意識不要）。 |

#### Datasets / Metadata / Evaluations

| 操作 | 注意 |
|------|------|
| `GET /datasets/{dataset_id}` | **`dataset_id`, `table_id`, `job_id`, `workspace_id`, `schema_version`, `dataset_payload`** を正。`dataset_payload` 内に MVP stub の `rows` 等が入りうる。OpenAPI `NormalizedDataset` のトップレベル `rows`/`trace_map` は **Phase 4 まで未対応の場合あり**。 |
| `GET /metadata/{metadata_id}` | **`metadata_id`, `dataset_id`, `review_points`, `dimensions`, `measures`, `decision`** を正。`grain` は **未投影**（Phase 4）。 |
| `GET /evaluations/{evaluation_ref}` | **`evaluation_ref`, `metadata_id`, `confidence_score`, `risk_signals`, `decision_recommendation`（オブジェクト）** を正。006 の `scores` / `explanation` / トップレベル `table_id` は **Phase 4**。 |

#### Review sessions

| 操作 | 注意 |
|------|------|
| `POST /review-sessions` | ボディは `metadata_id` のみ（MVP）。 |
| `GET .../review-sessions/{id}` | **`session_id`, `metadata_id`, `state`, snapshot 列**。 |
| `POST .../answers` | **Request**: OpenAPI **`TiMvpSubmitReviewAnswersRequest`**（`answers[]` に **`question_key` / `answer_value`** 必須、任意 **`mark_resolved`** / **`resolution_grade`**）。**Response 200**: **`TiMvpSubmitReviewAnswersResponse`**（`session` + 当リクエストで作成した **`TiMvpHumanReviewAnswer[]`**。行の **`id` は整数 PK**）。無印 `SubmitReviewAnswersRequest` は **006 将来用・deprecated**。 |
| `POST .../rerun` | **202** + `TiMvpJobSummary`。 |
| `GET .../suppression` | **JSON 配列**（ラッパなし）。要素形は `TiMvpSuppressionRecord`。 |

#### Suggestion runs

| 操作 | 注意 |
|------|------|
| `POST /suggestion-runs` | **主入力 `metadata_id`**。戻り **202** + `suggestion_run_ref`（`job_id` は MVP null 可）。 |
| `GET .../suggestion-runs/{ref}` | **`suggestion_run_id`, `metadata_id`, `analysis_candidates`, `suppression_applied`** を正。`table_id` は **空文字あり**。 |
| `GET .../candidates` | `candidates` + 条件付き `decision_recommendation`（011 JSON）。 |

### 18.4 フィールド分類（クライアント依存の指針）

#### 今すぐ依存してよい（安定意図・識別子・主フロー）

- **識別子**: `job_id`, `workspace_id`, `dataset_id`, `metadata_id`, `session_id`, `evaluation_ref`（= evaluation_id 値）, `suggestion_run_id` / path の `suggestion_run_ref`
- **Jobs**: `status`, `artifact_refs` の各キー（存在時）、`error_code` / `error_message`（失敗時）
- **Metadata**: `dataset_id`, `review_required`, `review_points`, `dimensions`, `measures`, `decision`（004 用 JSON）
- **Evaluation**: `decision_recommendation`（011・**オブジェクト**としてパース）
- **Suggestion**: `metadata_id`, `analysis_candidates`, `suppression_applied`
- **Review**: `state`, `review_required_snapshot`, `review_points_snapshot`
- **HTTP 慣習**: Jobs POST の **200/202**、rerun job の **201**、review rerun の **202**

#### TiMvp 暫定（動くが Phase 4 で見直し対象）

- **`current_stage`**: 実装固有文字列。006 の段階 enum と **1:1 対応しない**可能性。
- **`request_payload` 丸ごと**（クライアントは **読み取り専用・デバッグ**向け。新規ジョブの任意メタは将来 `input_parameters` 化しうる）
- **`request_payload.mvp_pipeline`**: MVP スナップショット。**正規の完了判定は `artifact_refs` + `status`** を推奨。
- **`dataset_payload`**: 003 の器。**006 の `rows`/`trace_map` トップレベル分離は Phase 4**。
- **suppression GET の「生配列」**: 将来 `SuppressionStateResponse` ラッパへ **移行しうる**（§16.2）。
- **answers の `question_key` / `answer_value`**: MVP の **事実契約**（OpenAPI `TiMvpReviewAnswerItem`）。006 `ReviewAnswer`（`point_id`, `answer_id` UUID 等）への **additive** 拡張余地あり。無印 `SubmitReviewAnswersRequest` は **将来ドラフト**（`deprecated`）。
- **`TiMvpHumanReviewAnswer.id`（整数 PK）**: 006 は `answer_id`（UUID 等）になりうる。
- **`/api/v1/*` 以外の API** のエラー: 引き続き DRF 既定（エンベロープなし）。

#### Phase 4 で追加される想定（006 準拠）

- **Jobs**: `kind`（`JobKind`）、トップレベルまたは冗長な `evaluation_ref` / `suggestion_run_ref`（ジョブ行スナップショット）、`table_id` のジョブ直下確定
- **HumanReviewSession**: `table_id`, `pending_questions`（または 006 相当の質問モデル）、取得時 `answers` の統合方針
- **ConfidenceEvaluation**: `scores`, `explanation`, トップレベル `table_id`（または辿れる ref の明文化）
- **NormalizedDataset**: トップレベル `rows` / `trace_map` / `normalization_status`（006 準拠）
- **AnalysisMetadata**: `grain` 等 006 必須フィールドの充足
- **エラー**: **012 拡張**（`message` / `request_id` / 細粒度 `error_code` を **additive**）

#### 将来非推奨化しそうなもの（計画レベル）

- ボディ **`idempotency_key`**（ヘッダへ一本化済み）
- ジョブ **`request_payload` への成果物スナップショット依存**（`mvp_pipeline` を **専用列 or ジョブ出力サブリソース**へ）
- **`confidence_score` 単一 float**（`scores` オブジェクトへ吸収しうる）
- suppression **配列直返し**（ラッパ + ページネーション）

※ 非推奨の実行は **少なくとも 1 リリースサイクルの警告期間**を置く（§18.5）。

### 18.5 Phase 4 移行計画（1 ページ）

**ゴール**: レスポンス形を **006（Phase 4 JSON Schema）** に揃え、OpenAPI の **`TiMvp*` と 006 名が一致**するか、**明示的な別スキーマ名**で併記される状態にする。

| 順序 | 対象 | 内容 | 理由 |
|:----:|------|------|------|
| P4-1 | **エラー（012）** | **済（OpenAPI 0.1.3 / 実装）**: `/api/v1/*` で `error_code` + `detail`（+ 任意 `errors`）。`message` / `request_id` は後続。他 `/api/*` は DRF 既定のまま。 | クライアント分岐の土台 |
| P4-2 | **OpenAPI と実装の一致** | **済（0.1.2）**: `TiMvpNormalizedDataset` / `TiMvpAnalysisMetadata` / `TiMvpConfidenceEvaluation` / `TiMvpHumanReviewSession` を components に定義し、該当 **GET** および **POST review-sessions 201** を **`TiMvp*` に紐付け**。無印スキーマは 006 目標形として維持。 | 生成コードと実装の乖離解消 |
| （附属） | **OpenAPI operation エラー列挙** | **済（0.1.4）**: 主要 operation に **401 / 400 / 404** を path 列挙。**403** は `components.responses.Forbidden` のみ（path には原則なし）。**409** は stale / 競合の **将来枠**として一部 path のみ（MVP 未広範囲を description で明記）。**job rerun** の 409 は削除（実装整合）。 | 契約可読性・生成クライアント・テスト観点 |
| P4-3 | **Jobs** | DB に `kind`（任意から必須へ）、レスポンスに `kind`。**`artifact_refs` は維持**しつつトップレベル ref を **additive** で追加可。 | 006 `JobRun` 整合 |
| P4-4 | **HumanReviewSession** | `table_id` / `pending_questions` を **additive**。既存 MVP フィールドは **維持**（破壊しない）。 | 005/006 整合 |
| P4-5 | **ConfidenceEvaluation** | `scores`, `explanation` を **additive**。`confidence_score` は非推奨期間後に削除検討。 | 011 完全投影 |
| P4-6 | **NormalizedDataset** | `rows`/`trace_map` をトップレベルへ（または 006 準拠の別リソース）。`dataset_payload` は **縮小 or 内部用**へ段階移行。 | 003 契約の明確化 |
| P4-7 | **Suppression GET** | `SuppressionStateResponse` を **正**とし、配列直返しは **deprecated**（`Accept` または `?format=` で切替も可）。 | API 一貫性 |

**非推奨期間（推奨運用）**

- **Deprecated 宣言**: OpenAPI `deprecated: true` + リリースノート。
- **最低 1 マイナーリリース**: 旧フィールド・旧形式を **引き続き返す**（読み専用）。
- **次マイナー以降**: 旧形式削除。必要なら **メジャーバージョン**（URL `/v2`）で一括破壊も可。

**互換維持方針**

- **原則 additive**（フィールド追加・optional 化）。削除は deprecated 期間後のみ。
- **破壊的変更**が必要な場合は **API メジャー**または **専用エンドポイント**（例: `/v1/.../compact` 廃止）。

**クライアント注意点**

- **`metadata_id` を suggestion の主キー**として保持し、`table_id` 空を許容。
- **ジョブ完了**は `status == SUCCEEDED` かつ **`artifact_refs` 非 null** を推奨（`mvp_pipeline` だけに依存しない）。
- **状態 enum** は未知値 tolerant。
- 生成クライアントは **OpenAPI 0.1.8 の path 既定（`TiMvp*`、review answers の **TiMvp request**、**401 は全 operation 列挙**、**409 は §13.1**—**`POST /suggestion-runs` の stale は実装済**、他は主に将来枠）** と **`ErrorResponse`（`error_code`）**、および **400/404** を先に採用し、無印の 006 目標スキーマは **参照・Phase 4 完了後の切替**に回すと安全。

### 18.6 Operation 単位の HTTP エラー（OpenAPI 0.1.4〜0.1.8）

OpenAPI の **各 operation の `responses`** に、次を **原則**として列挙する（詳細は `table-intelligence-openapi-draft.yaml` の該当 path）。

| 方針 | 内容 |
|------|------|
| **401** | **全 documented operation** に **`Unauthorized`**（`ErrorResponse`）を path 列挙（**0.1.7**）。文書全体に **`security: [tokenAuth]`** を設定。 |
| **400** | ボディ検証・整合エラーが起こりうる **POST**（jobs 開始、review session 作成、answers、suggestion run 開始、job rerun の body 等）に **`BadRequest`**。 |
| **404** | **ID 指定 GET**、**rerun**、**起点リソース不存在がありうる POST**（session 作成・suggestion 開始等）、**workspace 越境**はいずれも **同一の 404 応答**でマスク（`NotFound` / `TI_NOT_FOUND`）。 |
| **403** | **`Forbidden`** は **components.responses にのみ**残し、**各 operation には原則付けない**（MVP は 401 寄り）。将来、明示禁止が安定した path から **additive** で列挙する。 |
| **409** | **`Conflict`**（§13.1）。**実装済**: `startSuggestionRun`（**superseded `metadata_id`**）。**将来枠**: `submitReviewAnswers`、`review-sessions` の `rerun`。**GET `listSuggestionCandidates` には付けない**。**job rerun** には付けない。 |
| **default** | その他は **`ErrorResponseDefault`**（`TI_ERROR` 等）。 |

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-06 | 初版。実装接続フェーズの API 契約（原則・識別子・ライフサイクル・論理リソース・エラー・015 接続注記）。 |
| 0.1 追補 | 2026-04-07 | 015 整合: §2.4 に 015 行、§5.1.1 API／DB 列名対応、§15.2 ジョブ系表記、`evaluation_ref` 対応注記。 |
| 0.1 追補 2 | 2026-04-03 | §16: MVP 実装との契約差分表。OpenAPI 0.1.1 と役割分担を明文化。 |
| 0.1 追補 3 | 2026-04-03 | §18: OpenAPI 0.1.1 利用者ガイド、フィールド分類、Phase 4 移行計画（P4-1〜P4-7）。 |
| 0.1 追補 4 | 2026-04-03 | OpenAPI 0.1.2 / P4-2: GET dataset・metadata・evaluation・review-session と session POST 201 を `TiMvp*` schema に明示紐付け。§18・表を更新。 |
| 0.1 追補 5 | 2026-04-03 | P4-1: `/api/v1/*` エラー `error_code`+`detail`+`errors`。OpenAPI 0.1.3。§16.4・§18 更新。 |
| 0.1 追補 6 | 2026-04-03 | OpenAPI 0.1.4: 主要 operation に 401/400/404 列挙、`securitySchemes: tokenAuth`、403 は components のみ、409 は将来枠として限定・job rerun から 409 削除。§7.2・§16 優先順位・§18（§18.6・附属行）追補。 |
| 0.1 追補 7 | 2026-04-03 | OpenAPI 0.1.5: `TiMvpReviewAnswerItem` / `TiMvpSubmitReviewAnswersRequest`、answers POST の requestBody 紐付け。無印 `SubmitReviewAnswersRequest` を 006 向け `deprecated` に整理。§7.2・§10・§16.2・§18 更新。 |
| 0.1 追補 8 | 2026-04-03 | §13.1: `409 Conflict` の操作別マトリクス（A/B/C/D）、404/400 境界、MVP 未実装の明示。OpenAPI 0.1.6: `GET .../candidates` から 409 削除、`POST /suggestion-runs` に将来 409 追記。§16 優先順位・§18・§18.6 更新。 |
| 0.1 追補 9 | 2026-04-03 | [GUIDE-TI-table-intelligence-api-errors.md](./GUIDE-TI-table-intelligence-api-errors.md): 利用者向けエラー・HTTP 一覧（1 ページ）。§13 冒頭にリンク。TI 索引に登録。 |
| 0.1 追補 10 | 2026-04-03 | OpenAPI **0.1.7**: `GET /tables/*`・`GET /metadata/.../review-points` に **401** 追加（ガイドと列挙一致）。§16 優先順位・§18・§18.6・ガイド §1.3・§2.2・§2.5 更新。 |
| 0.1 追補 11 | 2026-04-03 | **`POST /suggestion-runs`**: superseded `metadata_id` を **409** + `TI_CONFLICT`（`artifact_relation` 判定）。OpenAPI **0.1.8**。§13.1 表・MVP 実装事実を更新。 |
| 0.1 追補 12 | 2026-04-07 | §9: **`GET .../decision`** を `judgment_result` 永続化と整合（未生成 **404**、`TI_TABLE_UNKNOWN`、011 分離）。OpenAPI `getJudgmentResult` / `JudgmentResult` schema 説明を追補。 |
| 0.1 追補 13 | 2026-04-07 | §9: **`GET .../read-artifact`** を `table_read_artifact` 永続化と整合（§9 表の連続性修正を含む）。OpenAPI `getTableReadArtifact` / `TableReadArtifact` 説明・example 追補。015 §7.4 MVP 追記。 |
| 0.1 追補 14 | 2026-04-07 | §9: read-artifact MVP 注記に **rerun 後の旧 table 404 可能性**を追補。015 §7.4: **read-artifact lineage**（`artifact_type=table_read_artifact`）を MVP 実装と整合。 |
