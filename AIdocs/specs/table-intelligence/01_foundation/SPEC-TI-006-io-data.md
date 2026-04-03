---
id: SPEC-TI-006
title: 入出力データ仕様書
status: Draft
version: 0.1
owners: []
last_updated: 2026-04-02
depends_on: [SPEC-TI-009, SPEC-TI-010]
---

## 1. 目的とスコープ

### 目的

表読取パイプラインから分析候補生成・人確認・永続化までの **全ステージのデータ契約**（エンティティ、必須フィールド、列挙値、版管理）の **単一参照源** を定義する。

### 本版（0.1）の位置づけ

**Phase 1 概念版**: エンティティ10前後の **識別子・必須フィールド・相互参照** を固定する。JSON Schema の完全パッケージ、全 DTO、OpenAPI 同期は **Phase 4** で本書を拡張する。

### スコープ外

- HTTP ステータス・認証（014）
- 物理テーブル・インデックス（015）
- 画面文言（007）

---

## 2. 関係仕様

| 仕様 | 関係 |
|------|------|
| SPEC-TI-009 | `taxonomy_code` 列挙の正本。 |
| SPEC-TI-010 | `HeadingTree` 構造の正本。 |
| SPEC-TI-012 | エラーコード列挙・マッピングの正本（012 骨格と相互に整合）。 |
| SPEC-TI-014/015 | 本書の DTO／エンティティを API・DB に投影。 |

---

## 3. 用語定義

| 用語 | 説明 |
|------|------|
| artifact | ステージ間で不変または版付きで受け渡す JSON 互換オブジェクト。 |
| schema_version | 契約の互換性を示す文字列（例: `ti.io.concept.v0_1`）。MAJOR 変更時に更新。 |
| trace | 原本セル・範囲への参照（001／003 のトレーサビリティ）。 |

---

## 4. 入力・前提

- 上流は **ファイルアップロード** またはストレージ参照（014 で詳細化）。
- 全エンティティは **テナント／ワークスペース ID**（概念）を持ちうるが、本概念版では `workspace_id` を任意フィールドとして置く。

---

## 5. 出力・成果物（概念エンティティ一覧）

以下は **必須フィールドのみ**（概念）。型は論理型。

### 5.1 File

| フィールド | 必須 | 説明 |
|------------|------|------|
| file_id | ✓ | 一意 ID。暫定: UUID（ULID 採否は §10）。 |
| name | ✓ | 元ファイル名。 |
| mime_type | ✓ | MIME。 |
| uploaded_at | ✓ | タイムスタンプ。 |
| schema_version | ✓ | 本書の版ラベル。 |

### 5.2 Sheet

| フィールド | 必須 | 説明 |
|------------|------|------|
| sheet_id | ✓ | |
| file_id | ✓ | 親 File。 |
| index | ✓ | 0 始まりシート順。 |
| title | | シート名。 |

### 5.3 TableCandidate

| フィールド | 必須 | 説明 |
|------------|------|------|
| table_id | ✓ | |
| sheet_id | ✓ | |
| bbox | ✓ | シート座標系の矩形（001 が正本、ここは参照）。 |
| read_artifact_ref | ✓ | TableReadArtifact への参照または埋め込み ID。 |

### 5.4 TableReadArtifact

| フィールド | 必須 | 説明 |
|------------|------|------|
| artifact_id | ✓ | |
| table_id | ✓ | |
| cells | ✓ | セル辞書または配列（詳細は 001）。 |
| merges | ✓ | 結合セル一覧。 |
| parse_warnings[] | ✓ | 空配列可。 |

### 5.5 HeadingTree

| フィールド | 必須 | 説明 |
|------------|------|------|
| heading_id | ✓ | |
| table_id | ✓ | |
| taxonomy_code | ✓ | 009 の enum。 |
| nodes | ✓ | ノードマップ。 |
| cell_bindings | ✓ | データセルとの対応。 |

### 5.6 JudgmentResult

| フィールド | 必須 | 説明 |
|------------|------|------|
| judgment_id | ✓ | |
| table_id | ✓ | |
| decision | ✓ | `AUTO_ACCEPT` \| `NEEDS_REVIEW` \| `REJECT`（002／011 と同一語彙）。 |
| taxonomy_code | ✓ | |
| evidence[] | ✓ | 証跡参照（ルール ID、セル範囲等）。 |

### 5.7 NormalizedDataset

| フィールド | 必須 | 説明 |
|------------|------|------|
| dataset_id | ✓ | |
| table_id | ✓ | |
| rows[] | ✓ | 論理行。 |
| trace_map | ✓ | 行・列から原本への写像（003）。 |

### 5.8 AnalysisMetadata

| フィールド | 必須 | 説明 |
|------------|------|------|
| metadata_id | ✓ | |
| dataset_id | ✓ | |
| grain | ✓ | **004 が意味正本**。1行の意味の宣言。 |
| dimensions[] | ✓ | 空配列可だが 004 の制約に従う。 |
| measures[] | ✓ | 同上。 |

### 5.9 HumanReviewSession

| フィールド | 必須 | 説明 |
|------------|------|------|
| session_id | ✓ | |
| table_id | ✓ | |
| state | ✓ | ステートマシン（005）。 |
| pending_questions[] | ✓ | |

### 5.10 JobRun

| フィールド | 必須 | 説明 |
|------------|------|------|
| job_id | ✓ | |
| kind | ✓ | `READ` \| `JUDGE` \| `NORMALIZE` \| `META` \| `SUGGEST` 等。 |
| status | ✓ | `PENDING` \| `RUNNING` \| `SUCCEEDED` \| `FAILED`。 |
| table_id | | 対象。 |
| error_code | | 012 参照。 |

---

## 6. 列挙値（概念・ドラフト）

### taxonomy_code

009 の `TI_TABLE_*` をそのまま使用（詳細は 009）。

### decision（Judgment）

- `AUTO_ACCEPT`
- `NEEDS_REVIEW`
- `REJECT`

### job status

- `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`

（012 でエラーコードと組み合わせを固定。）

---

## 7. 例外・エラー・フォールバック

- すべての失敗は **012 のコード** で表現し、本書のエンティティでは `error_code` / `parse_warnings` / `REJECT` のいずれかで運ぶ。
- **部分成功**: 同一 `JobRun` 内で複数テーブルがある場合の粒度は Phase 4 で確定（暫定: テーブル単位で成功／失敗を分離）。

---

## 8. テスト観点

- 各エンティティについて **最小 JSON 例** が 008 のフィクスチャ命名規則に従う。
- `schema_version` が変わった場合の **後方互換ポリシー**（読み手が未知フィールドを無視できるか）を Phase 4 で明文化。

---

## 9. 未確定事項（暫定案）

| 論点 | 暫定案 |
|------|--------|
| UUID vs ULID | **UUID** を既定。分散ジョブで順序が要る場合 ULID を検討。 |
| イベントソーシング | **採用しない**（MVP）。履歴は JobRun＋監査ログで代替検討。 |
| HeadingTree の埋め込み vs 参照 | 同一レスポンス内は **埋め込み**、DB は 015 で正規化。 |

---

## 10. 次版（Phase 4）で追加する章

- 統合 JSON Schema パッケージのディレクトリ構成
- 014 エンドポイントごとの DTO 対応表
- 015 テーブル／カラム対応表
- 監査ログフィールド一覧

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-02 | Phase1 概念版。エンティティ10＋列挙ドラフト。 |
