---
id: SPEC-TI-003
title: 変換・正規化仕様書
status: Draft
version: 0.2.5
owners: []
last_updated: 2026-04-07
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-006, SPEC-TI-009, SPEC-TI-010]
---

## 文書目的

[SPEC-TI-001](SPEC-TI-001-table-read.md) の `TableReadArtifact` と [SPEC-TI-002](SPEC-TI-002-judgment.md) の `JudgmentResult`（および 002 が evidence で渡す一次ラベル・見出し前提・単位スコープ）を入力とし、**分析および後続 AI 処理で扱いやすい内部形式**へ**変換・正規化する規約の正本**を定義する。

**責務境界（正本）**

- **[SPEC-TI-001](SPEC-TI-001-table-read.md)** は**候補抽出と一次構造化**（セル・結合・観測属性・`parse_warnings`）までである。  
- **[SPEC-TI-002](SPEC-TI-002-judgment.md)** は**採否・分類・一次判定**（`taxonomy_code`、行種別、列役割、単位候補、`decision`／`evidence`）までである。  
- **本仕様（003）** は**変換と正規化**（論理行生成、縦持ち、型整備、`trace_map`）の正本である。003 は表種別の**再確定**や見出しの**再判定**を行わない。

---

## スコープ

- 一覧表の**内部表現**への変換方針
- クロス集計表の**縦持ち**変換方針
- 帳票型・`TI_TABLE_KEY_VALUE`・001 が許容する **1×N／N×1 例外表**の正規化方針
- **多段見出し**の展開方針（010 の `HeadingTree`／`cell_bindings` に依存）
- **行種別**・**列役割**に基づく**変換経路選択**
- **単位候補**の継承と **002 の `UNIT_SCOPE_*`** に沿った適用範囲
- **集計行**・**注記行**・**見出し帯**と**表外要素**（タイトル・注記ブロック等）の**データ本体からの分離／別保持**
- **数値・日付・文字列**の型正規化（確定閾値・スコアは含めない）
- **空白・結合・稀疏 cells** 前提での正規化
- **元セル位置**とのトレーサビリティおよび **`trace_map` の設計方針**
- **`TI_TABLE_UNKNOWN`** および **`JudgmentResult.decision === NEEDS_REVIEW`** 時の**変換制約**と**暫定出力**
- **NormalizationResult**（006 では `NormalizedDataset`）の**出力構造方針**
- **004／005／011／013** へ引き継ぐ事項の明示

---

## 非スコープ

以下は本書で**細部まで固定しない**。委譲先を明記する。

- **表種別の確定ロジック**（[SPEC-TI-002](SPEC-TI-002-judgment.md)／[SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md)）
- **見出し候補の採否**（002）、**HeadingTree の JSON Schema 完成形**（[SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md)／006 Phase4）
- **UI の具体表示**・利用者向け文言（[SPEC-TI-007](../05_experience_quality/SPEC-TI-007-ui.md)）
- **HTTP**・**ジョブ API**（[SPEC-TI-014](../04_system/SPEC-TI-014-api.md)）
- **DB 物理設計**（[SPEC-TI-015](../04_system/SPEC-TI-015-db.md)）
- **信頼度スコアの数式**・重み・閾値（[SPEC-TI-011](SPEC-TI-011-confidence-scoring.md)）
- **人確認画面の具体文言・ステップ詳細**（[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md)）
- **分析候補生成ロジックの詳細**（[SPEC-TI-013](../03_analysis_human/SPEC-TI-013-suggestion-generation.md)）
- **dimensions／measures／grain の意味の最終確定全体**（[SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md)）

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 内部正規表現 | [SPEC-TI-006 §5.7](../01_foundation/SPEC-TI-006-io-data.md) の `NormalizedDataset`（`rows[]`＋`trace_map`）が担う論理表現。 |
| NormalizationResult | 本書およびパイプライン説明上の**正規化成果物**を指す語。006 の必須契約における型名は **`NormalizedDataset`** である。 |
| 論理行 | `rows[]` の 1 要素。元表の 1 明細行に相当する場合と、縦持ちにより **1 交差×1 度量** に相当する場合がある。 |
| 縦持ち | クロス表などから、**軸キー列＋度量列（および単位メタ）** への変換。複数交差セルが複数論理行になる。 |
| 稀疏表現 | `cells` に**存在するセルのみ**を列挙し、格子の欠損セルは**列挙されない**表現。欠損は**空値と同義**として扱う（§空白・結合・稀疏表現の扱い）。 |
| 部分正規化 | 表の一部のみ `rows[]` を生成し、残りを **skipped／INCOMPLETE** としてメタに残す状態。 |
| ルール ID | 正規化根拠の追跡用識別子（例: `N3-TAX-001`）。初版では箇条書き中心。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-001](SPEC-TI-001-table-read.md) | **`TableReadArtifact` 正本**。セル値・結合・**0-based inclusive 座標**の観測の参照源。003 は**改変しない**。 |
| [SPEC-TI-002](SPEC-TI-002-judgment.md) | **`JudgmentResult` 正本**。taxonomy・行種別・列役割・単位・`decision`／`evidence` を**変換入力**とする。003 は判定を**再実行しない**。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | `NormalizedDataset` の**必須フィールド**（`dataset_id`, `table_id`, `rows[]`, `trace_map`）の正本。 |
| [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) | **分類語彙**と**タイプ別後続方針**。003 は **経路選択**に用いる。 |
| [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) | **見出し木・`cell_bindings`** の構造正本。多段展開・縦持ちキーはこれに依存。 |
| SPEC-TI-004 | **grain・dimensions／measures の意味正本**。003 は**候補材料**まで。 |
| SPEC-TI-005 | **人確認**。003 は正規化不能・曖昧性を**構造化して渡す**前提を満たす。 |
| SPEC-TI-011 | **信頼度**。003 は不確実性を**特徴量として**出力に載せうる。 |
| SPEC-TI-013 | **分析候補生成**。003 の論理表現を入力とするが、生成ロジックは 013 正本。 |

### [SPEC-TI-002](SPEC-TI-002-judgment.md) との接続境界（要約）

- **002 が 003 に渡すもの**: `evidence[]` の **`J2-ROW-001` / `J2-COL-001`**（`by_row_index` / `by_column_index`）。MVP では materialize がこれを **`dataset_payload.normalization_input_hints`** に**畳んで**参照させる。**候補ヒントであり、一次判定の確定ではない**。  
- **003 が用いてよいもの（002 由来）**: **行／列 index ベース**のヒント、（001 と併せ）**`raw_display` の転記**、**`column_slots` の参照面**。  
- **003 が単独で確定しないもの**: **taxonomy の最終意味**、**dimension／measure**、**業務意味**、**merges／多段見出しの解決**（§入力の理想形・経路選択は別途；MVP は §MVP 実装接続）。  
- **委譲**: **不一致・曖昧さを 003 が抱え込まず**、`trace_map`・**レビュー**（[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md)）・**上位仕様**へ逃がす。002 側の整理は **[SPEC-TI-002](SPEC-TI-002-judgment.md)** の「003 に引き継ぐ事項」を参照。

---

## 正規化の位置づけ

表解析パイプラインにおいて、003 は次に限定する。

1. **001 の観測を尊重**: `cells`／`merges`／`parse_warnings` を**真実**として参照し、捏造しない。  
2. **002 のラベルを消費**: `taxonomy_code`・行種別・列役割・`UNIT_SCOPE_*` を**変換パラメータ**として使う。  
3. **010 の構造に従う**: `HeadingTree`／`cell_bindings` が利用可能なら、展開・縦持ちは **binding 優先**。  
4. **追跡可能性**: 各論理値が**どの原本セル（範囲）に由来するか**を `trace_map` で失わない。  
5. **ゲーティング連携**: `NEEDS_REVIEW` でも**無理に完全正規化せず**、§UNKNOWN / NEEDS_REVIEW 時の扱いに従う。

**再掲**: **001＝候補と一次構造化**、**002＝採否・分類・一次判定**、**003＝変換・正規化**。

---

## 入力

### 必須

- **`TableReadArtifact`**（006 §5.4、[SPEC-TI-001](SPEC-TI-001-table-read.md) 準拠）— `cells`, `merges`, `parse_warnings[]`  
- **`JudgmentResult`**（006 §5.6、[SPEC-TI-002](SPEC-TI-002-judgment.md) 準拠）— `taxonomy_code`, `decision`, 非空の `evidence[]`  
- **`table_id`**（001／002 と同一）  
- **座標系**: **0-based inclusive**（001 に準拠）。`trace_map` も同一系で記述する。

### 推奨（あれば利用）

- **`HeadingTree`**（006 §5.5、[SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md)）— `cell_bindings` がある場合、縦持ち・多段展開の主入力。  
- **002 の `evidence[].details`** — 行種別マップ、列役割マップ、単位候補、`UNIT_SCOPE_*`、`ambiguity` 等（006 MINOR または暫定 JSON）。

### MVP 実装接続（backend）

以下は **現行 backend の MVP スタブ**（`NormalizedDataset.dataset_payload` 上の出力）に限定した**契約の要約**である。§入力の「必須／推奨」や **経路選択**（`taxonomy_code` 主軸）と述べる**理想の 003**とは**境界が異なる**。より詳細な契約・テスト観点は同ディレクトリの `MEMO-TI-003-mvp-*.md` を参照してよい。

#### MVP の公式入力（backend スタブ）

- **主入力**: `dataset_payload.normalization_input_hints`（002 の J2-ROW / J2-COL 由来の **`by_row_index` / `by_column_index`**。候補ヒントであり**意味確定ではない**）。  
- **補助入力**: 同一テーブル最新 `TableReadArtifact.cells` の **`raw_display`**（データ行について **`values["c{N}"]` への転記**にのみ使用）。  
- **行走査の補助**: **`by_row_index` が空**のときのみ、`TableScope` の **`row_min` / `row_max`**（0-based inclusive）で行 index を列挙する。  
- **現 MVP で直接読まないもの**: `JudgmentResult.evidence` 全文の再解釈、`taxonomy_code`、`decision`、`merges`（materialize がヒントへ畳んだ後の `normalization_input_hints` 以外の 002 直参照）。

#### MVP の最小出力と「確定しない」範囲

| 出力 | 役割（MVP） | まだ確定しないもの（例） |
|------|-------------|---------------------------|
| **`rows[]`** | ヒントに従い**データ行**を列挙し、`c{N}` に **001 の転記結果**を載せる（スキップ行は含めない）。 | 型正規化、論理列 ID、grain、[SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md) における dimensions／measures の意味確定。 |
| **`trace_map[]`** | スキップ行・セル転記・列ヒントの**説明責任**（`trace_ref`、`kind`、行／列 index）。 | 監査ログの正本、002／004 の最終判定の置換。 |
| **`column_slots[]`** | **列カタログ／参照面**（列 index と `cN` の対照、任意で `hint_from_002` と trace 参照）。 | dimension／measure の割当、taxonomy 連動、**表の全列の網羅**。 |

#### `rows[]` / `trace_map[]` / `column_slots[]` の責務境界（MVP）

- **`rows[]`** は**転記結果**（論理行＋`values`）。  
- **`trace_map[]`** は**説明責任**（`rows` に載らない事実・セル粒度の根拠を含む）。  
- **`column_slots[]`** は**列対照表**（`cN` と列 index の対応および候補ヒントの参照）。  
- **`dimensions`／`measures`、taxonomy、業務意味の確定**は 004／002／009 等の**別層**（MVP は **`semantic_lock_in: false`**）。

#### `column_slots[]` の MVP 契約（要点）

- **列カタログ／参照面**であり、**dimension／measure の意味確定ではない**。  
- **スロット集合**は **`normalization_input_hints.by_column_index` のキー**と、**`rows[].values` に転記された列**（`cN` から復元した index）の**和集合**とする。  
- 各要素に **`semantic_lock_in: false`**（004 への意味ロックインではない）。  
- **`slot_id` の恒久フォーマット**や論理列 ID への昇格は本 MVP では固定しない（下記「未解決」）。

#### MVP で未解決の論点（上位委譲）

`merges` の解釈、**多段見出し**、**taxonomy 連動**に基づく経路、**業務意味**（004）、**`slot_id` の恒久化**／論理列スキーマは、**現 MVP では解決せず**、上位層・後続仕様・人確認へ**委譲**する。

---

`normalization_input_hints` は **`JudgmentResult.evidence`（J2-ROW-001 / J2-COL-001）由来**の入力ヒントとして materialize で `dataset_payload` に載せ、003 スタブが参照する。

同一ジョブの materialize では、`dataset_payload.normalization_input_hints` に 002 の **J2-ROW / J2-COL**（`by_row_index` / `by_column_index`）を載せ、MVP 正規化スタブが **`rows[]`** と **`trace_map`** に次を載せうる: **`header_band_skipped`**、**`note_candidate`**、**`skipped_row_candidate`**（集計行）、**`attribute_column_candidate`** / **`measure_column_candidate`**（その他列は **`column_role_hint`**）。**004 の `dimensions`／`measures` 確定ではない**（`semantic_lock_in: false` を付けうる）。スキーマ識別子の例: `ti.mvp_normalization_stub.v1`。

#### `rows[].values` の列キーと `column_slots[]`（MVP）

- **`rows[].values` のキー**は当面 **`c{N}`**（0-based 列 index）を**互換の正**として維持する。既存クライアント・転記ロジックとの整合のため、**本段階では `values` キーを論理列 ID に置き換えない**。  
- **論理列への将来接続**のため、`dataset_payload` に **`column_slots[]`**（仮称・[SPEC-TI-006 §5.7](../01_foundation/SPEC-TI-006-io-data.md)）を**並置しうる**。各要素の**最小スキーマ**（いずれも 003 の入力／変換補助であり、**004 の意味確定ではない**）:  
  - **`slot_id`**: 安定しうるスロット識別子（MVP 例: `col_{N}`）。  
  - **`table_column_index`**: 001／002 と共有する **0-based inclusive** 列 index。  
  - **`values_key`**: 対応する **`rows[].values` のキー**（通常 `c{N}`）。  
  - **任意** **`hint_from_002`**: `normalization_input_hints.by_column_index` に対応する J2-COL ラベル文字列。  
  - **任意** **`trace_ref_ids`**: 当該列に関連する `trace_map[].trace_ref` の列挙（説明責任）。  
  - **任意** **`trace_kind_preview`**: 当該列に関連する `trace_map[].kind` の要約（実装便宜）。  
- **スロット集合**: `by_column_index` のキーと、実際に **`values` に転記された列**（`cN` から復元した index）の**和集合**とする。  
- スキーマ識別子の例: `ti.mvp_column_slots.v1`（`mvp_normalization_stub` メタと併記しうる）。

### 入力の優先順位（矛盾時）

1. **001 の観測**（セル値・結合）を最優先。002 の断定と矛盾する場合は正規化結果に **conflict メタ**を付し、005 連携を前提とする。  
2. **`taxonomy_code`** は**単一値**として経路選択に用いる（副候補は evidence のみ。002 Draft 0.2 方針に整合）。  
3. **010 の binding** が 001 と整合する場合は binding を採用。整合しない場合は §UNKNOWN / NEEDS_REVIEW 時の扱いおよび **INCOMPLETE** 伝播。

---

## 出力

### 主成果物

006 §5.7 の **`NormalizedDataset`**（本書では **NormalizationResult** と同義の概念）。必須フィールド: `dataset_id`, `table_id`, `rows[]`, `trace_map`。

### 副次成果物（006 MINOR または `normalization_meta` 等の拡張）

- **`normalization_status`**: `COMPLETE` \| `PARTIAL` \| `FAILED`（列挙値の固定は 006 Phase4）  
- **`skipped_regions[]`**, **`aggregate_rows[]`**, **`note_blocks[]`**, **`incomplete_bindings[]`**, **`type_normalization_notes[]`**, **`unit_application[]`** の概念— §NormalizationResult の構造方針および各節を参照。

---

## 正規化の原則

1. **非破壊**: 001 の Artifact を上書きしない。  
2. **非判定**: 002 の taxonomy／見出し採否を覆さない。矛盾はメタに記録。  
3. **座標一貫**: 全 trace は **0-based inclusive**。  
4. **説明責任**: 主要な論理値は `trace_map` にエントリを持つ。`rows[]` に含めない行（集計・注記）も**別出力先＋参照**で失わない。  
5. **タイプ別経路**: [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) の後続方針に沿い**主経路**を選択する。  
6. **無理な補完禁止**: 欠落見出しを確定値で埋めず、INCOMPLETE／`PARTIAL` を伝播する。

---

## 正規化対象の表種別

003 が**経路選択の入力**とする `taxonomy_code`（009 の `TI_TABLE_*`）のうち、初版で明示的に扱う対象は次である。

| taxonomy_code（代表） | 003 での位置づけ |
|------------------------|------------------|
| `TI_TABLE_LIST_DETAIL` | 一覧の内部表現（ワイド行＋型正規化）。 |
| `TI_TABLE_CROSSTAB` | 縦持ち変換の主対象。 |
| `TI_TABLE_TIME_SERIES` | 縦持ちまたはワイド保持の分岐対象（§変換経路選択方針の TIME_SERIES 補足）。 |
| `TI_TABLE_KEY_VALUE` | キー値形式への正規化。 |
| `TI_TABLE_FORM_REPORT` | ブロック／セクション単位の部分正規化。 |
| `TI_TABLE_PIVOT_LIKE` | **LIST_DETAIL 寄りの経路を既定**とし、階層・小計は `aggregate_rows[]` 等へ（§変換経路選択方針の PIVOT_LIKE 補足）。 |
| `TI_TABLE_LOOKUP_MATRIX` | スパース長形式（行キー・列キー・セル値）。 |
| `TI_TABLE_UNKNOWN` | 完全正規化を行わず §UNKNOWN / NEEDS_REVIEW に従う。 |

**明記**: **語彙の定義・境界**は 009／002 正本であり、003 は**新ラベルを増やさない**。

---

## 変換経路選択方針

- **第一キー**: `JudgmentResult.taxonomy_code`（単一値）。  
- **第二キー**: 002 の行種別・列役割・単位スコープ・`decision`／evidence の `ambiguity`。  
- **第三キー**: 010 の `cell_bindings` の有無と完全性。  
- **分岐表（初版・主経路）**:

| taxonomy_code | 主経路（003） |
|----------------|----------------|
| `TI_TABLE_LIST_DETAIL` | ワイド行保持＋多段見出し展開＋型正規化。 |
| `TI_TABLE_CROSSTAB` | 縦持ち（行軸キー＋列軸キー＋度量）。binding 必須に近い。 |
| `TI_TABLE_TIME_SERIES` | **時系列列が反復的・規則的に並ぶ**場合は**縦持ち優先**。**識別子列を固定のまま横に残す価値が高い**（比較軸として不可欠）場合は**ワイド保持を許容**。最終の時間意味は 004。 |
| `TI_TABLE_KEY_VALUE` | 単一レコード羅列なら 1 論理行（ワイド化）。同一キー種の繰り返しなら縦長キー値。§帳票型 / KEY_VALUE / 1×N / N×1 の正規化を参照。 |
| `TI_TABLE_FORM_REPORT` | セクション単位の部分正規化（§帳票型 / KEY_VALUE / 1×N / N×1 の正規化の Draft 0.2 補足）。`skipped_regions` を付与しやすい。 |
| `TI_TABLE_UNKNOWN` | §UNKNOWN / NEEDS_REVIEW 時の扱いの**暫定標準**に従う。 |

競合時は **`normalization_status=PARTIAL`** とし、複数解釈はメタに残して 005 へ渡す。

### TIME_SERIES の分岐メモ（Draft 0.2）

- **縦持ちを選んだか／ワイドを選んだか**は、**`normalization_meta` 内の経路メモ**（暫定キー例: `time_series_layout_choice`）または **`type_normalization_notes[]`** に**残す**（004／011／013 が下流で解釈しうる）。  
- **数式・閾値の固定は行わない**。判断根拠は**短文**でよい。

### PIVOT_LIKE の扱い（Draft 0.2）

- **既定経路**: **LIST_DETAIL に近いワイド（またはそれに準ずる論理行）**を優先し、**004／013 が橋渡ししやすい**形を取る。  
- **階層・小計**: **`aggregate_rows[]`** および**パス由来の補助メタ**（level・ラベル参照等、006 Phase4 で型固定）に載せ、**明細 `rows[]` との混在**を避けうる。  
- **ネスト JSON による表現**は**Draft 0.2 の既定としない**（過度な複雑化を避ける）。必要な階層情報は **`PARTIAL`**＋補助メタで補う。  
- **完全な意味解釈**は 004、**候補の出し方**は 013 に委譲。

---

## 一覧表の正規化

- **対象**: 主に `TI_TABLE_LIST_DETAIL`、および `TI_TABLE_TIME_SERIES` のワイド保持モード。  
- **行**: `ROW_DETAIL` を**データ `rows[]` の母集団**とする。集計・注記・見出し帯は §集計行・注記行の扱い。  
- **列**: 多段見出しは §多段見出しの展開方針。002 の `COL_*` タグを論理列メタに引き継ぐ。  
- **型**: §型正規化。  
- **trace_map**: 各論理フィールド → 元の 1 セルまたは結合範囲（アンカー規約は 001）。

---

## クロス集計表の正規化

- **対象**: `TI_TABLE_CROSSTAB`。  
- **縦持ち 1 論理行**: **行軸の合成キー**、**列軸の合成キー**、**度量値**（＋§単位候補の継承と適用範囲）。  
- **入力**: 010 の `cell_bindings` を優先。`row_path`／`column_path` からキャプションを解決。  
- **空セル**: 稀疏表現では欠損セルは `cells` に現れない。論理行を**値のある交差のみ**生成するか、NULL 明示行を出すかは製品方針で決める。初版では**値のあるセルのみ行生成**を推奨し、外挿は解析側に委ねる。  
- **trace_map**: 論理フィールドごとに**見出しセル**と**交差セル**の両参照を許容（配列等。006 Phase4 で形式固定）。

---

## 帳票型 / KEY_VALUE / 1×N / N×1 の正規化

- **`TI_TABLE_FORM_REPORT`（Draft 0.2 部分正規化の基準）**: **キー値対が比較的明確なブロック**は **`rows[]` 化候補**。**セクション見出し中心**でデータ格子が弱いブロックは **`skipped_regions`** または**構造メタ**（ブロック境界・見出しテキストの参照）へ。**説明文中心**のブロックは **`note_blocks[]` 寄り**とする。**帳票を無理に一覧表化しない**。判定が割り切れない場合は **`normalization_status=PARTIAL`** とし、ブロック単位で**分離保持**して 005 へ渡す。タイトル・注記は §集計行・注記行の扱いと `note_blocks[]` で保持。  
- **`TI_TABLE_KEY_VALUE`**: taxonomy を再判定しない。レイアウトから経路のみ選択— **単一レコード**なら 1 論理行ワイド化。**繰り返しキー値**なら縦長（キー列＋値列）。曖昧なら `PARTIAL`。  
- **1×N／N×1**: 001 が例外として許容した候補で 002 が**表として採用**したものだけを正規化対象とする。`REJECT` 済みは §UNKNOWN / NEEDS_REVIEW 時の扱い。系列が**ラベル＋値**パターンなら KEY_VALUE 経路に寄せる。  
- **表外要素**: `region_hints` 由来のタイトル・注記は、データ格子の `rows[]` に**混在させず**、メタまたは `note_blocks[]` に分離する方針を推奨。

---

## 多段見出しの展開方針

- **前提**: [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) の **level**（外側ほど小）と**継承**。  
- **LIST_DETAIL（初版推奨）**: 外側から内側へ **個別の key 列**に対応させる（`column_path`／`row_path` の各ノードを論理列へ写像）。単一連結キーにまとめるのは例外時のみ。区切り文字は製品で一貫させる。  
- **欠落・空 caption**: 列を捏造しない。NULL／空を許容し、metadata に記録。`INCOMPLETE` binding は論理行を生成しないか `incomplete_bindings[]` に列挙。  
- **CROSSTAB／縦持ち**: パス各段を key fields（行軸・列軸）へ写像。  
- **002 が不採用とした見出し**は展開対象に含めない。

---

## 行種別・列役割の反映方針

### 行種別（002 暫定 enum に整合）

| 行種別 | 003 の扱い |
|--------|------------|
| `ROW_DETAIL` | `rows[]` の通常データ行。 |
| `ROW_SUBTOTAL` / `ROW_GRAND_TOTAL` | **既定**: `rows[]` から除外し **`aggregate_rows[]`** に保持。製品方針で包含する場合はフラグで切替。 |
| `ROW_NOTE` | `rows[]` に含めず **`note_blocks[]`** 等にテキスト＋原本参照。 |
| `ROW_HEADER_BAND` | データ行化しない。見出し展開の入力のみ。 |
| `ROW_UNKNOWN` | 除外＋メタ（`decision` と連動）。 |

### 列役割

- `COL_ATTRIBUTE` → キー列（dimension 候補）。  
- `COL_MEASURE` → 度量候補。縦持ち後は measure 名＋値の再配置がありうる。  
- `COL_TIME` → 時間軸候補。型正規化は 003、意味は 004。  
- `COL_UNIT` → 列全体単位のヒント（§単位候補の継承と適用範囲）。  
- `COL_NOTE` → データから分離し注記メタへ。  
- `COL_UNKNOWN` → 004 で再分類。003 は無理に型を確定しない。

---

## 単位候補の継承と適用範囲

002 の仮ラベル（[SPEC-TI-002](SPEC-TI-002-judgment.md)）を引き継ぐ。

| 仮ラベル | 作用範囲 | 003 の反映 |
|----------|----------|------------|
| `UNIT_SCOPE_TABLE` | **表全体** | 全論理行または全度量列に共通単位メタ。`trace_map` は単位元セル（行）を指す。 |
| `UNIT_SCOPE_COLUMN` | **特定列** | 対象列に属する論理フィールドへ単位を付与。 |
| `UNIT_SCOPE_CELLS` | **特定セル群** | bbox に一致する論理値のみに単位を付与。 |

**競合**時は単位を付けず、`type_normalization_notes[]` に記録し **005 連携を推奨**。

---

## 集計行・注記行の扱い

- **集計行**: 既定では `rows[]` と分離し **`aggregate_rows[]`** に**ラベル・値・原本参照**を残す（消去しない）。  
- **注記行**: `rows[]` に含めない。**`note_blocks[]`** にテキストと**0-based inclusive の原本参照**を載せる。  
- **見出し帯**: データ行にしない。キー側 `trace_map` のみ。  
- **表外要素**（キャプション、シート注記）: 正規化対象データと**別保持**。005 が原本を表示しうる形で trace を残す。

---

## 型正規化

- **数値**: カンマ、通貨記号、括弧負数等の除去ルールは locale／012 に委譲。パース失敗時は**原文保持＋失敗フラグ**（011 入力）。  
- **日付**: ISO 8601 への正規化を推奨。曖昧な表記は原文保持＋警告メタ。  
- **文字列**: 前後空白除去、改行 LF 正規化を推奨。全角半角統一は列単位オプション。  
- **確定閾値**（どこまでを数値確定とするか）は **011／製品**。003 はルールベースの試行に留める。

---

## 空白・結合・稀疏表現の扱い

- **稀疏 cells**: 001 の標準プロファイルでは **`cells` は存在セルのみ**。格子に存在しない座標は**空セルと同義**として読む。003 は**欠損セルを捏造しない**。  
- **結合**: **`merges` が正本**。代表セル（アンカー）規約は [SPEC-TI-001](SPEC-TI-001-table-read.md)。結合領域内の従属座標に**論理値を複製**する場合も、各論理値は **`trace_map` で原本セルを区別**する。  
- **被覆セルの重複列挙**: 001 は結合を **`merges` で表現**し、同一セルを二重に `cells` に載せない前提とする。003 はその前提に依存する。  
- **空白行／列**: 002 の行種別・見出し帯判定に従い、データ行として採用しないか `skipped_regions` で記録。

---

## trace_map / 元セル参照の保持方針

- **目的**: 正規化後の各論理フィールドが、**元のどのセルまたは矩形**から来たか機械的に追跡できること。  
- **座標系**: **0-based inclusive**（001 と同一）。  
- **001／002 との整合**: 001 の座標と 002 の `targets`／evidence を**同一系**で参照できること。003 は新しい座標系を導入しない。  
- **追跡の観点（Draft 0.2）**: 少なくとも次を **`trace_map` で区別しうる**こと（JSON の完成形は 006 Phase4）。  
  - **キー由来フィールド**（見出し・軸・識別子）の trace  
  - **値由来フィールド**（度量・セル実値）の trace  
  - **単位由来メタ**（単位セル・単位行）の trace  
  - **集計／注記／見出し展開由来**（`aggregate_rows[]`・`note_blocks[]`・見出し帯から複製したキー）の trace  
- **1 論理値 → 複数原本セル**: **許容**（例: CROSSTAB の交差＋見出し、結合補完）。配列・エントリ分割は Phase4 で固定。  
- **粒度**: セル単位を最小。  
- **必須性**: 006 で `trace_map` が必須のため、**`rows[]` に現れる全値**についてエントリを持つことを成立ラインとする。  
- **`parse_warnings`**: 001 の warnings を改変せず、参照 ID または座標で evidence／メタと接続する。

---

## UNKNOWN / NEEDS_REVIEW 時の扱い

### 制約

- **無理に完全正規化しない**。単一解釈へ収束させない。  
- **`TI_TABLE_UNKNOWN`（暫定標準・Draft 0.2）**: **最小限の暫定正規化**（セルフラット列挙など）または **`normalization_status=PARTIAL`** の**いずれかを許容**。002 の `decision`・evidence に従い、**005 へ渡す情報**（`skipped_regions`・`ambiguity`・`parse_warnings` 参照）を**失わない**。  
- **`NEEDS_REVIEW`**: **部分正規化を許可**する。`PARTIAL`＋`incomplete_bindings`／`skipped_regions`／`ambiguity` の伝播。  
- **`JudgmentResult.decision === REJECT`（暫定標準・Draft 0.2）**: **原則として正規化成果物（`NormalizedDataset`）を生成しない**。または **`normalization_status=FAILED` 相当の最小成果物**（`table_id`・空に近い `rows[]`・メタのみ等）に**留める**。**002 の `REJECT` と整合**させる。  
- **UNKNOWN と REJECT の差**、および**成果物の有無**の**最終契約**は **[SPEC-TI-012](../01_foundation/SPEC-TI-012-errors.md)／[SPEC-TI-014](../04_system/SPEC-TI-014-api.md)** で確定する前提とする（本書は**003 側の暫定運用**を明記するまで）。

### 暫定出力に留める条件

- 必須 binding 欠落、CROSSTAB で軸再構成不能、複数単位競合、型パース大量失敗など— **安全な論理行のみ**出力し残りはメタへ分離。

### 人確認へ渡す保持情報

- `normalization_status`、`skipped_regions[]`、`incomplete_bindings[]`、`aggregate_rows[]`、`note_blocks[]`、`type_normalization_notes[]`、002 由来の `ambiguity`、001 の `parse_warnings` 参照。

---

## NormalizationResult の構造方針

006 の型名は **`NormalizedDataset`** である。本書の **NormalizationResult** はこれと**同一の成果物**を指す。

| フィールド（006 必須） | 003 での意味 |
|------------------------|--------------|
| `dataset_id` | 正規化実行の一意 ID。 |
| `table_id` | 入力と同一。 |
| `rows[]` | 論理行。各要素は **key fields**（軸・識別子）、**value fields**（度量・カテゴリ値）、**metadata fields**（行種別タグ、単位、パース失敗フラグ等）の**概念区分**を載せうる（物理キー名は 006 Phase4）。 |
| `trace_map` | 論理フィールド → 原本セル（範囲）の写像。 |

### `rows[]` の最低限の論理構造（Draft 0.2）

**1 論理行**は、実装者が**最小レコード**をイメージできるよう、少なくとも次の**群**を**持ちうる**（すべて必須とは限らない。物理キー名・JSON Schema は **006 Phase4**）。

| 群 | 含みうる内容（概念） |
|----|----------------------|
| **識別用の行単位情報** | 論理行 ID、元行インデックス、パイプライン内の通番等（006 で固定）。 |
| **キー群** | 多段見出し由来の軸値、KEY_VALUE のキー、CROSSTAB 縦持ち後の行軸・列軸キー等。 |
| **値群** | 度量・カテゴリの実値。**縦持ち**では **`measure 名`（または列 ID）と `measure 値` のペア**を取りうる（004 が正式な measure 名を宣言するまでの**中継表現**）。 |
| **メタ群** | 行種別タグ、単位、パース失敗、002 由来の列役割タグ、`normalization_status` 行レベルフラグ等。 |

**明記**: **grain の宣言**と dimension／measure の**最終命名**は [SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md)。003 は上記区分を揃えた**材料**を渡す。

**拡張メタ（006 MINOR 推奨）**: `normalization_status`, `skipped_regions[]`, `aggregate_rows[]`, `note_blocks[]`, `incomplete_bindings[]`, `type_normalization_notes[]`, `unit_application[]`, **`normalization_meta`（経路選択メモ等）** — **005／011／013** が消費しうる構造を目指す。

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| `grain`・dimensions／measures の意味・禁止組合せ | SPEC-TI-004 |
| 人確認ステップ・質問・PATCH・画面フロー | SPEC-TI-005 |
| 信頼度の式・閾値・ログ | SPEC-TI-011 |
| 分析候補の生成／抑制ロジック | SPEC-TI-013 |
| エラーコード・HTTP・ジョブ失敗 | SPEC-TI-012／014 |
| `NormalizedDataset`／`trace_map` の JSON Schema 完全形 | SPEC-TI-006 Phase4 |
| 表タイプの定義・境界 | SPEC-TI-009／002 |

---

## レビュー観点

- 001 の座標系と `trace_map` が一貫しているか。  
- 002 の行種別・列役割・`UNIT_SCOPE_*` が無視されていないか。  
- 稀疏 `cells` と `merges` 前提が矛盾なく説明されているか。  
- taxonomy ごとの主経路が 009 の後続方針と齟齬ないか。  
- CROSSTAB 縦持ちで交差セルと見出しの trace が両立しているか。  
- 集計・注記が `rows[]` 外でも失われないか。  
- UNKNOWN／NEEDS_REVIEW 時に完全正規化へ無理に収束していないか。  
- 004／005／011／013 への委譲が重複していないか。

---

## 初版成立ライン

- 入力が `TableReadArtifact`＋`JudgmentResult` に限定され、006 の `NormalizedDataset` 必須フィールドを満たす**方針**が述べられている。  
- **LIST_DETAIL** と **CROSSTAB** の主経路が文章化されている。  
- **帳票型・KEY_VALUE・1×N／N×1** の扱いが箇条書き以上である。  
- **多段見出し・行種別・列役割・単位スコープ・型・空白／結合／稀疏**が扱われている。  
- **`trace_map` と 0-based inclusive** が明記されている。  
- **UNKNOWN／NEEDS_REVIEW** 時の制約と暫定出力が整理されている。  
- **NormalizationResult（`NormalizedDataset`）** の構造方針がある。  
- 004／005／011／013 への委譲が明確。

**Draft 0.2 追加確認**: **`rows[]` 最低限の群**、**trace_map の観点別粒度**、**TIME_SERIES／FORM_REPORT／PIVOT_LIKE** の補足、**UNKNOWN と REJECT の暫定出力差**が参照できること。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.2.5 | 2026-04-07 | §関連仕様書に 002 との接続境界（ヒント／畳み込み／確定しない範囲／trace・review 委譲）を最小追記。 |
| 0.2.4 | 2026-04-07 | MVP 契約の要約を §「MVP 実装接続」に追記（公式入力・最小出力・責務境界・`column_slots` 要点・未解決の上位委譲）。 |
| 0.2.3 | 2026-04-03 | `rows[].values` は当面 `cN` 維持。将来の論理列用に `dataset_payload.column_slots[]` を並置しうる旨（最小スキーマ・004 非確定）。 |
| 0.2.2 | 2026-04-08 | MVP trace `kind` 細分化（`header_band_skipped` / `note_candidate` / 列候補）。`normalization_input_hints` の evidence 由来を明記。 |
| 0.2.1 | 2026-04-08 | MVP 接続: `normalization_input_hints` からスタブが `rows`/`trace_map` にスキップ行・列役割ヒントを載せうる旨（`ti.mvp_normalization_stub.v1`）。 |
| 0.2 | 2026-04-17 | `rows[]` 最低限の論理構造、trace_map 観点別追跡、TIME_SERIES 分岐メタ、FORM_REPORT 部分正規化基準、UNKNOWN／REJECT 暫定標準（012／014 前提）、PIVOT_LIKE 既定経路・aggregate 分離。004／005／011／013 中継粒度の補強。 |
| 0.1 | 2026-04-03 | Draft 初版本文。001/002 境界、26 章立て、稀疏・結合前提、trace_map、taxonomy 経路、単位・集計・注記、UNKNOWN/NEEDS_REVIEW、NormalizationResult、委譲。 |

---

## 補足メモ（初版の外枠）

### この初版で未確定の論点

- `rows[]` の物理キー命名と JSON Schema（006 Phase4）。  
- `trace_map` の JSON 表現（1 対 1／1 対多、範囲型）。  
- `REJECT` 時の**省略 vs 最小 FAILED 成果物**の**014／012 上の最終契約**（003 は暫定標準を記載済み）。  
- CROSSTAB の空交差を論理行に含めるか（NULL 行）の製品既定。  
- `normalization_meta` の**正式キー集合**（経路メモ・PIVOT パスメタ）。
