---
id: SPEC-TI-006
title: 入出力データ仕様書
status: Draft
version: 0.5
owners: []
last_updated: 2026-04-21
depends_on: [SPEC-TI-009, SPEC-TI-010]
---

## 1. 目的とスコープ

### 目的

表読取パイプラインから分析候補生成・人確認・永続化までの **全ステージのデータ契約**（エンティティ、必須フィールド、列挙値、版管理）の **単一参照源** を定義する。

### 本版（0.1）の位置づけ

**Phase 1 概念版**: エンティティ10前後の **識別子・必須フィールド・相互参照** を固定する。JSON Schema の完全パッケージ、全 DTO、OpenAPI 同期は **Phase 4** で本書を拡張する。

### 本版（0.2）の追補（Step 1）

**座標参照の概念**（`CellRef`／`CellRangeInclusive`、0-based inclusive）、**`TraceRef` の種別分離方針**（幾何／論理／ID）、**`normalization_status` の暫定三値**、**`decision` と `decision_recommendation` の分離**、**参照種別の用語**を本文に追加した。**`evidence[]`／`review_points` 等の完全 Schema**は **Step 2** 以降とし、**Phase 4** で JSON Schema を厳密化する。

### 本版（0.3）の追補（Step 2-A）

**`JudgmentResult.evidence[]` の Phase 4 第1版の枠組み**（完全 Schema は未固定）、**`NormalizedDataset` の主要副次メタ候補**（必須化はしない）、**`AnalysisMetadata.review_points[]` 要素の最小構造**、**`HumanReviewSession.state` の暫定 enum 候補**を本文に追加した。**禁止遷移**・**`answers[]` 詳細**・**ConfidenceEvaluation／SuggestionSet`**は **Step 2-B／Step 3** に残す。

### 本版（0.4）の追補（Step 2-B）

**`NormalizedDataset` 副次配列の要素型方向・配列必須／任意**（§5.7.2）、**`review_points[]` の Schema 寄り整理**（§5.8.1 拡張）、**`HumanReviewSession.answers[]` 最小構造**（§5.9.1）、**`human_review_session_state` 禁止遷移の下書き**（§6）、**`ConfidenceEvaluation` 器**（§5.10）を追加した。**`SuggestionSet`**・**`evaluation_ref`／`suggestion_run_ref`**・**014／015 対応表の実填**は **Step 3** に残す。

### 本版（0.5）の追補（Step 3）

**`SuggestionSet` 器**（§5.11）、**`JobRun` の `evaluation_ref`／`suggestion_run_ref`**（§5.12）、**014／015 を見据えた意味上の参照契約**（§5.0）、**Step 1〜3 の段階的追加の整理**（§1 本節直後の小節）を追加した。**014／015 の DTO・テーブル実填**は **Phase 4** に残す。

### Step 1〜3 の段階的追加（責務の整理）

- **Step 1**: **座標系**（`CellRef`／`CellRangeInclusive`）、**`TraceRef` 種別**、**`decision`／`decision_recommendation` 分離**。**幾何と一次判定語彙の共有基準**にとどまり、**アルゴリズム・完全 Schema は 006 単体では固定しない**。
- **Step 2-A／2-B**: **`JudgmentResult.evidence[]`**、**`NormalizedDataset` 副次メタ**、**`review_points[]`／`answers[]`**、**`ConfidenceEvaluation`**、**セッション状態・禁止遷移下書き**。**各ステージの器と 002／003／004／005／011 正本の接続**。**数式・完全 JSON Schema は 006 単体では固定しない**。
- **Step 3**: **`SuggestionSet`**、**ジョブ文脈の `evaluation_ref`／`suggestion_run_ref`**、**014／015 に必要な意味上のリンク前提**。**013 正本の候補構造を器として受ける**のみ。**DTO・RDB 列・完全 Schema は書かない**。
- **006 は段階的にフィールドを足しても、002〜005・011・013 の正本責務を越境して上書きしない**。

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
| SPEC-TI-011 | `ConfidenceEvaluation` の **`scores`・`explanation` の意味・生成規則の正本**。本書 §5.10 はその**器と参照契約**を受ける。 |
| SPEC-TI-013 | `SuggestionSet`・**`analysis_candidates[]` の意味・生成規則の正本**。本書 §5.11 はその**器と参照契約**を受ける。 |
| SPEC-TI-014/015 | 本書の **意味上のエンティティ・参照キー**を **DTO／永続化**に投影。**物理形の最終決定**は 014／015。 |

---

## 3. 用語定義

| 用語 | 説明 |
|------|------|
| artifact | ステージ間で不変または版付きで受け渡す JSON 互換オブジェクト。 |
| schema_version | 契約の互換性を示す文字列（例: `ti.io.concept.v0_1`）。MAJOR 変更時に更新。 |
| trace | 原本セル・範囲・論理フィールド・ID 等への参照の総称。§3.2・§3.3。 |

### 3.1 セル座標と矩形（`CellRef`／`CellRangeInclusive`）

- **CellRef**: 単一セルを表す参照。**行インデックス**および**列インデックス**から成る。**行・列ともに 0-based**（先頭行・先頭列を 0 とする）。
- **CellRangeInclusive**: 軸平行の矩形範囲。**`row_min`**, **`row_max`**, **`column_min`**, **`column_max`**（いずれも 0-based）で表し、**四辺とも inclusive**（端点を含む）。
- **共有基準**: [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) の `bbox`・セル座標、[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の `trace_map`、[SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md) の `review_points[].trace_refs` が**幾何を指す場合**は、本節の **0-based inclusive** に従う（各仕様が意味・生成規則の正本）。
- **A1 形式**（例: `A1:B2`）は**人間向けの補助表現**であり、**機械可読な正本ではない**。

### 3.2 参照種別（幾何・論理・ID）

本書 **Step 1** で固定するのは**区別の原則**である。**完全な JSON Schema**は **Phase 4** で厳密化する。

| 種別 | 説明 | 主に現れる仕様群 |
|------|------|------------------|
| **幾何参照** | `CellRef`／`CellRangeInclusive` 等。**原本シート上のセル／範囲**を指す。 | 001（`bbox`, `cells`）, 002（`evidence[].targets`）, 003（`trace_map`）, 004（`trace_refs` が幾何を指す場合） |
| **論理参照** | 論理列・`dimensions[]`／`measures[]` 上のパス等。**分析意味上のフィールド**を指す。 | 004（メタ、`affected_fields`）, 013（`required_fields`／`optional_fields`） |
| **ID参照** | `point_id`, `rule_id`, warning code, `evaluation_id`, **`evaluation_ref`**, **`suggestion_run_ref`**, `suggestion_run_id` 等の**識別子**による参照。 | 002（`evidence`）, 004（`review_points`）, 005（セッション）, 011（`explanation` 内 `refs`）, §5.12（`JobRun` 成果物参照） |

### 3.3 `TraceRef`（参照種別付き union の概念）

- **`TraceRef`** は単一の平坦型ではなく、**参照種別（discriminant）を伴う union 的概念**として扱う。
- **最低限、次の 3 系統を区別**する: **幾何参照**、**論理参照**、**ID参照**。
- **Phase 4** で JSON Schema（`oneOf` 等）を厳密化する。**Step 1** の本文責務は**種別分離の原則**の固定にとどめる。
- [SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md) の `trace_refs`、[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) の explanation 内参照、[SPEC-TI-013](../03_analysis_human/SPEC-TI-013-suggestion-generation.md) の候補 `evidence[]` は、**将来この整理に接続する**前提とする。

---

## 4. 入力・前提

- 上流は **ファイルアップロード** またはストレージ参照（014 で詳細化）。
- 全エンティティは **テナント／ワークスペース ID**（概念）を持ちうるが、本概念版では `workspace_id` を任意フィールドとして置く。

---

## 5. 出力・成果物（概念エンティティ一覧）

以下は **必須フィールドのみ**（概念）。型は論理型。

### 5.0 参照契約と 014／015（Step 3）

本書は **HTTP・OpenAPI・RDB の物理定義**を書かない（**014／015**）。

**ここで固定するのは意味上のリンク関係であり、実装形式（JSON キー名の最終形・埋め込み／参照 URL・テーブル列名・外部キー制約の有無）ではない**。

- **`evaluation_ref`**: **`ConfidenceEvaluation.evaluation_id`** と**同一キー空間**の **ID参照**。**信頼度評価の成果物**をジョブ実行から辿るためのリンク。
- **`suggestion_run_ref`**: **`SuggestionSet.suggestion_run_id`** と**同一キー空間**の **ID参照**。**候補生成ランの成果物**をジョブ実行から辿るためのリンク。
- **`dataset_id`・`metadata_id`・`session_id`・`table_id`**: 下流が **正規化結果・分析メタ・人確認・テーブル単位**を束ねるときの**安定識別子**。**014 のレスポンス／015 の永続化**で相互参照可能であることが前提（**スキーマ詳細は 014／015**）。

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
| bbox | ✓ | シート座標系の矩形（001 が正本、ここは参照）。**幾何は §3.1 の 0-based inclusive**（`CellRangeInclusive` 概念に一致）。 |
| read_artifact_ref | ✓ | TableReadArtifact への参照または埋め込み ID。 |

### 5.4 TableReadArtifact

| フィールド | 必須 | 説明 |
|------------|------|------|
| artifact_id | ✓ | |
| table_id | ✓ | |
| cells | ✓ | セル辞書または配列（詳細は 001）。**キー／座標は §3.1 の 0-based**。 |
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
| decision | ✓ | **002 の一次判定**。語彙は §6 **`decision`（Judgment）**。**§6 `decision_recommendation` とは別 enum・別概念**。 |
| taxonomy_code | ✓ | |
| evidence[] | ✓ | 証跡参照（ルール ID、セル範囲等）。**幾何は §3.1、種別分離は §3.3**（Phase 4 で Schema 化）。**各要素の枠組みは §5.6.1**。 |

#### 5.6.1 `evidence[]` の要素（Phase 4 第1版の枠組み・Step 2-A）

[SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) における**判定の説明根拠**を載せる配列。**完全な JSON Schema・細かい型**は **Phase 4** で厳密化する。**Step 2-A** では、各要素が**次のキーを扱いうる**前提を固定する（**いずれも必須ではない**組合せは 002 正本）。

| キー（概念） | 役割 |
|--------------|------|
| `rule_id` | ルール・根拠の識別子（**ID参照**）。 |
| `conclusion` | 当該証跡が支持する結論の要約（人間可読短文等）。 |
| `targets` | セル／範囲への**幾何参照**。**§3.3 `TraceRef` の幾何系**と整合（0-based inclusive は §3.1）。 |
| `refs_parse_warnings` | [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) の `parse_warnings` へのリンク。 |
| `details` | 構造化された補足（JSON。副候補 taxonomy 等は 002 正本）。 |
| `confidence_hint` | 判定強度のヒント（任意スカラー等）。 |

**011** の **`explanation`**（信頼度説明）は **別オブジェクト**であるが、**`rule_id`／`refs` 等で参照接続**しうる。**`evidence[]` 自体は 002 の出力契約**である。

### 5.7 NormalizedDataset

| フィールド | 必須 | 説明 |
|------------|------|------|
| dataset_id | ✓ | |
| table_id | ✓ | |
| rows[] | ✓ | 論理行。 |
| trace_map | ✓ | 行・列から原本への写像（003）。**原本への幾何は §3.1 と共有**（003 が正本）。 |

#### 5.7.1 主要副次メタ候補（Step 2-A）

[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の成果物に付随しうる**副次メタ**のうち、**パイプライン下流と接続しやすい主要候補**を次に列挙する。**Step 2-A ではいずれも「必須フィールド」として固定しない**。**要素型・配列の必須／任意**は **§5.7.2** に集約する。

| フィールド（概念） | 説明 |
|--------------------|------|
| `normalization_status` | §6 の暫定三値。 |
| `skipped_regions[]` | 正規化対象外となった範囲。 |
| `incomplete_bindings[]` | 未確定の binding。 |
| `aggregate_rows[]` | 集計行の扱い。 |
| `note_blocks[]` | 注記ブロック。 |
| `type_normalization_notes[]` | 型正規化の注記。 |
| `unit_application[]` | 単位適用のスコープ。 |

#### 5.7.2 副次メタの要素型方向・配列必須／任意（Step 2-B・Phase 4 第1版レベル）

**完全な JSON Schema の固定は行わない**。**各配列は `NormalizedDataset` 上で任意**（**省略可**または**空配列**）。**`normalization_status`** は **スカラー**（§6）であり配列ではない。

| フィールド | 配列の必須 | 要素が担う情報 | 要素の最低限必須候補（概念） |
|------------|------------|----------------|------------------------------|
| `skipped_regions[]` | **任意** | 正規化対象外とした **幾何範囲** と理由 | **`range`**（`CellRangeInclusive`、§3.1）、**`reason`**（短文）または **`reason_code`**（機械可読コード）のいずれか |
| `incomplete_bindings[]` | **任意** | **見出し・データセル対応**が未確定であることの記録 | **`binding_kind`**（どの binding 系統か）、**`trace_refs`**（§3.3、少なくとも 1 件） |
| `aggregate_rows[]` | **任意** | **集計行・小計行**として扱う論理行の識別 | **`row_ref`**（論理行インデックスまたは 003 が定める行キー）、**`aggregate_role`**（例: `SUBTOTAL`／`TOTAL`／`HEADER_LIKE` 等・語彙は 003 正本） |
| `note_blocks[]` | **任意** | **脚注・注記ブロック**（表外テキストの塊） | **`text`**、**`anchor`**（幾何 `CellRangeInclusive` または論理アンカーのいずれか） |
| `type_normalization_notes[]` | **任意** | **型正規化**（桁落ち・丸め・解釈）に関する説明 | **`field_path`**（論理列／measure 上のパス）、**`note`**（短文または構造化オブジェクトのいずれか） |
| `unit_application[]` | **任意** | **単位**がどの論理列・どの範囲に適用されるか | **`target`**（論理列 ID または measure キー）、**`unit`**（単位表現文字列またはコード）、**`scope`**（行部分集合・**省略可**） |

### 5.8 AnalysisMetadata

| フィールド | 必須 | 説明 |
|------------|------|------|
| metadata_id | ✓ | |
| dataset_id | ✓ | |
| grain | ✓ | **004 が意味正本**。1行の意味の宣言。 |
| dimensions[] | ✓ | 空配列可だが 004 の制約に従う。 |
| measures[] | ✓ | 同上。 |
| review_points[] | | **人確認論点**（[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md) のキュー入力）。**要素の契約は §5.8.1**。**必須ではない**（004 正本が生成タイミングを定める）。 |

#### 5.8.1 `review_points[]` の要素（Schema 寄り整理・Step 2-B）

[SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md) が生成し、[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md) が **`point_id` 単位**のキューとして **dequeue／解消**する入力。**完全な JSON Schema**は **Phase 4** で固定する。

| キー（概念） | 型の方向 | 役割 |
|--------------|----------|------|
| `point_id` | **文字列 ID**（安定一意） | 005 のセッション内で **1 論点 = 1 ID**。**`answers[].point_id`** と突合する。 |
| `category` | **列挙または限定文字列** | 論点の分類。**語彙の正本は 004**。 |
| `priority` | **整数**（小さいほど先）または **順序 enum** | **作業キューの並び**に使う次元。 |
| `severity` | **列挙**（例: INFO／WARN／BLOCKER 等・語彙は 004／005 で確定） | **影響の重さ・ブロッキング性**に使う次元。 |
| `affected_fields` | **文字列パスの配列** | **論理フィールド**（`dimensions[]`／`measures[]` 上のパス等）。 |
| `trace_refs` | **`TraceRef` 概念の配列**（§3.3） | 幾何・論理・ID の混在可。**幾何は §3.1**。 |
| `suggested_resolution_type` | **列挙または限定文字列** | 再実行・差し戻し先のヒント。**005 が分岐に使いうる**。 |

**`priority` と `severity` の暫定方針**: **代替関係ではない**。**両方を持ちうる**（**`priority`** = キュー順序、**`severity`** = 事象の重さ）。**片方のみ**の要素も許容する。**両方ある場合**の並び替えは **一次キー `priority`**、**同点時に `severity` を二次キー**としうる（**最終ルールは 005**、**API のソートは 014**）。

### 5.9 HumanReviewSession

| フィールド | 必須 | 説明 |
|------------|------|------|
| session_id | ✓ | |
| table_id | ✓ | |
| state | ✓ | **§6 `human_review_session_state`** および **§6 禁止遷移の下書き**。[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md) の状態概念をデータ契約へ寄せる。**最終 state machine は未確定**。 |
| pending_questions[] | ✓ | |
| answers[] | | **人の回答ログ**（最小構造は §5.9.1）。**必須ではない**（**空配列**可）。**UI 文言・API 入力形式は 014／005 に委譲**。 |

#### 5.9.1 `answers[]` の要素（最小構造・Step 2-B）

**005** の **`point_id`** と **1:1 または 1:多**（同一論点の再回答は **`answer_id`** で区別）。**画面ラベル・リクエスト DTO**は **014** で確定する。

| キー（概念） | 役割 |
|--------------|------|
| `answer_id` | 回答レコードの一意 ID。 |
| `point_id` | 対象論点。**`review_points[].point_id`** と一致。 |
| `answer_type` | 選択肢／自由記述／範囲指定等の**区分**（列挙は 005／014）。 |
| `selected_option` | 選択肢 ID 等（**`answer_type` が選択のとき**）。 |
| `free_text` | 自由記述（**`answer_type` がテキストのとき**）。 |
| `region_ref` | **幾何回答**（**`CellRangeInclusive`／`CellRef`**、§3.1）。**`answer_type` が範囲のとき**。 |
| `answered_by` | 主体 ID（ユーザー／サービスプリンシパル等・014 正本）。 |
| `answered_at` | タイムスタンプ（RFC3339 等・型は Phase 4）。 |

**`answer_type` に応じて、`selected_option`・`free_text`・`region_ref` のうち回答内容を表す 1 系統を用いる**（**他は省略または空**）。**複合回答**が要る場合は **005** が**複数の `answers[]` 要素**に分割するか**拡張**する（**検証は 014／005**）。

### 5.10 ConfidenceEvaluation（信頼度評価・器）

[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) が **スコア計算・説明生成の正本**である。**本エンティティは 011 の出力を受ける器**および **他エンティティからの参照契約**を 006 で固定する。**内部アルゴリズム**は 011。

| フィールド | 必須 | 説明 |
|------------|------|------|
| evaluation_id | ✓ | 一意 ID。 |
| table_id | ✓ | 対象テーブル。 |
| scores | ✓ | **多次元スコアの束**（オブジェクトまたは配列）。**内部の完全 Schema**は **Phase 4**（011 がキー設計の正本）。 |
| decision_recommendation | ✓ | §6 **`decision_recommendation`**。 |
| explanation | ✓ | **011 の `explanation` 構造をそのまま格納する器**（ネスト・`refs` 等は **011 正本**）。 |
| feature_snapshot_hash | | **再現性**のための入力特徴のハッシュ（**任意**・アルゴリズムは 011／運用で確定）。 |

### 5.11 SuggestionSet（分析候補・器）

[SPEC-TI-013](../03_analysis_human/SPEC-TI-013-suggestion-generation.md) が **候補生成・抑制・フィールド要件の意味正本**である。**本エンティティは 013 の出力を受ける器**であり、**`confidence`・`priority`・`readiness` の数式・重み・閾値は 013 に委譲**する。**完全な JSON Schema**は **Phase 4**。

| フィールド | 必須 | 説明 |
|------------|------|------|
| suggestion_run_id | ✓ | 当該候補生成ランの一意 ID。**`JobRun.suggestion_run_ref`**（§5.12）と同一キー空間。 |
| table_id | ✓ | 対象テーブル。 |
| analysis_candidates[] | ✓ | 分析候補のリスト（**空配列**可）。**要素構造は §5.11.1**。 |
| suppression_applied[] | ✓ | **抑制**の適用記録（**空配列**可）。**要素の詳細形は 013 正本・Phase 4**。 |

#### 5.11.1 `analysis_candidates[]` の要素（概念フィールド・Phase 4 未固定）

| キー（概念） | 役割 |
|--------------|------|
| `candidate_id` | 候補の一意 ID。 |
| `category` | 候補の分類（**013 正本の語彙**）。 |
| `priority` | 提示順・扱い優先のヒント（**数式・重みは 013**）。 |
| `confidence` | 信頼度のスカラーまたは構造体（**内部形は Phase 4・013**）。 |
| `readiness` | 実行可能度・準備状態（**語彙・判定は 013**）。 |
| `required_fields[]` | 必須とみなす論理フィールド（**論理参照**・§3.2）。 |
| `optional_fields[]` | 任意の論理フィールド。 |
| `evidence[]` | 根拠トレース（**§3.3 `TraceRef` 概念**に接続）。 |
| `risk_notes[]` | リスク・注意の短文または構造化ノート。 |
| `followup_questions[]` | フォローアップ質問（**005／014 と接続しうる**）。 |

### 5.12 JobRun

| フィールド | 必須 | 説明 |
|------------|------|------|
| job_id | ✓ | |
| kind | ✓ | `READ` \| `JUDGE` \| `NORMALIZE` \| `META` \| `SUGGEST` 等。 |
| status | ✓ | `PENDING` \| `RUNNING` \| `SUCCEEDED` \| `FAILED`。 |
| table_id | | 対象。 |
| error_code | | 012 参照。 |
| evaluation_ref | | **`ConfidenceEvaluation` 成果物**への **ID参照**（**`evaluation_id`** と同一キー）。**§5.0**。**API／DB での載せ方は 014／015**。 |
| suggestion_run_ref | | **`SuggestionSet`／候補生成ラン**への **ID参照**（**`suggestion_run_id`** と同一キー）。**§5.0**。**API／DB での載せ方は 014／015**。 |

**`evaluation_ref`／`suggestion_run_ref` は任意**。**ジョブ種別・成功時のみ**付与されうる。**同等のジョブ文脈**（監査ログ等）へ写す場合も **同一の ID 意味**を保つ（**物理カラム名は未定**）。

---

## 6. 列挙値（概念・ドラフト）

### taxonomy_code

009 の `TI_TABLE_*` をそのまま使用（詳細は 009）。

### decision（Judgment）

**002** の `JudgmentResult.decision` に用いる列挙（一次判定の正本は 002）。

- `AUTO_ACCEPT`
- `NEEDS_REVIEW`
- `REJECT`

### decision_recommendation（011・信頼度）

**011** の出力で用いうる**推奨語彙**。**上記 `decision`（Judgment）とは別 enum** として扱う（**綴りが同形でも同一列挙型とみなさない**）。

- `AUTO_ACCEPT`
- `NEEDS_REVIEW`
- `REJECT`

**011 は 002 の `decision` を上書きする正本ではない**。**一次判定と推奨の採用順**は **014／製品ポリシー**で定める。

### normalization_status（正規化・暫定 enum）

[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の `NormalizedDataset` で用いる前提の**暫定**三値。**副次配列の要素型方向**は **§5.7.2**。

- `COMPLETE`
- `PARTIAL`
- `FAILED`

### human_review_session_state（人確認セッション・暫定 enum 草案・Step 2-A）

**005** の `HumanReviewSession.state` に用いうる**暫定**候補。

- `OPEN`
- `IN_PROGRESS`
- `WAITING_RERUN`
- `PARTIALLY_RESOLVED`
- `RESOLVED`
- `CLOSED_UNRESOLVED`
- `ESCALATED`

#### 禁止遷移（下書き・Step 2-B）

**本小節は下書き**であり**最終版ではない**。**完全な state machine**・**REST での遷移トリガ**・**例外手続き**は **[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md)** および **014** に委譲する。

- **`RESOLVED` のあと `IN_PROGRESS` に戻さない**（再オープンが要る場合は**新規セッション**または **005／014 が定める監査付き手順**）。
- **`CLOSED_UNRESOLVED` 到達後**は**通常のオペレーションでは状態を編集しない**（変更は **005／014** の別フロー）。
- **`WAITING_RERUN` から `OPEN` へ直接遷移しない**（**再実行完了**や **005 が定める中間状態**を経由する）。
- **`ESCALATED` は通常系ワークフロー主軸とは別ルート**とし、**単純な自動遷移表への無条件合流を置かない**（合流条件は **005／014**）。

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
| 0.5 | 2026-04-21 | Step 3: §5.11 `SuggestionSet`・§5.11.1 候補要素、`JobRun` の `evaluation_ref`／`suggestion_run_ref`（§5.12）、§5.0 014／015 意味リンク、§1 Step 1〜3 整理、§2 に 013 行・014／015 行拡張、§3.2 ID 行拡張。`JobRun` 節番号 §5.12 へ繰下げ。 |
| 0.4 | 2026-04-03 | Step 2-B: §5.7.2 副次配列の要素型・必須／任意、§5.8.1 `review_points[]` 整理（`priority`／`severity` 暫定方針）、§5.9.1 `answers[]`、§6 禁止遷移下書き、§5.10 `ConfidenceEvaluation`、§5.11 `JobRun`、§2 に 011 行。 |
| 0.3 | 2026-04-20 | Step 2-A: `evidence[]` 枠組み（§5.6.1）、`NormalizedDataset` 副次メタ候補（§5.7.1）、`review_points[]` 最小構造（§5.8.1）、`human_review_session_state` 草案（§6）。§5.8 に `review_points[]` 行（任意）、§5.9 `state` 説明更新。 |
| 0.2 | 2026-04-19 | Step 1: `CellRef`／`CellRangeInclusive`・0-based inclusive、`TraceRef` 種別分離、`normalization_status` 三値、`decision`／`decision_recommendation` 分離、参照種別用語（§3）。§5.3〜5.7 説明列の最小追記。 |
| 0.1 | 2026-04-02 | Phase1 概念版。エンティティ10＋列挙ドラフト。 |
