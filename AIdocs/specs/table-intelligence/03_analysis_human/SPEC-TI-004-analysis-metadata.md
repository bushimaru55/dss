---
id: SPEC-TI-004
title: 分析メタデータ仕様書
status: Draft
version: 0.2.5
owners: []
last_updated: 2026-04-07
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-003, SPEC-TI-005, SPEC-TI-006, SPEC-TI-009, SPEC-TI-010, SPEC-TI-011, SPEC-TI-013]
---

## 文書目的

[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の **`NormalizedDataset`**（および 003 が付随させうる正規化メタ）を**主入力**とし、[SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) の **`JudgmentResult`** を**補助入力**として、**分析可能な意味構造**（`dimensions`／`measures`／`grain`／time axis／category axis／`filters`／`available_aggregations`／`inferred_business_meaning`／`review_required`／`review_points`）を定義する**正本**とする。

**004 の責務（要約）**

- **分析エンジン・人確認・信頼度・分析候補生成**が共通参照できる **`AnalysisMetadata`** を組み立てる。  
- **001 の生読取結果（`TableReadArtifact`）を主入力にしない**。原本説明は **003 の `trace_map` 経由**で間接参照する。  
- **005** は `review_required`／`review_points` の**消費者**（フロー・UI 正本は 005／007）。**011** はスコア式の正本。**013** は候補生成ロジックの正本。004 はこれらの責務を**奪わない**。

---

## スコープ

- **`AnalysisMetadata` の目的と位置づけ**（パイプライン内での役割）  
- **003 から受け取る内容**・**002 から受け取る内容**の整理  
- **`dimensions`／`measures`／`grain`** の定義方針と相互境界  
- **time axis**／**category axis**／**filters** の識別と宣言方針  
- **`available_aggregations`**（許容集計の宣言）  
- **`inferred_business_meaning`**（推定業務意味の扱い）  
- **`review_required`／`review_points`** の判定・生成方針  
- **005／011／013** への**引き継ぎの考え方**  
- **`AnalysisMetadata` の構造方針**（006 必須フィールドとの整合）  
- **001〜003／005／011／013** との**責務境界**

---

## 非スコープ

- **読取・判定・正規化のロジック本体**（001〜003）  
- **信頼度スコア式**（011）、**候補生成アルゴリズム**（013）  
- **taxonomy・見出しモデルの正本定義**（009／010／002）  
- **人確認 UI・具体質問文**（005／007）  
- **API・DB 物理設計**（014／015）

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 分析メタデータ | [SPEC-TI-006 §5.8](../01_foundation/SPEC-TI-006-io-data.md) の `AnalysisMetadata` および本書が推奨する拡張プロパティの総称。 |
| dimension 候補 | 003 の **key fields** や **metadata** 由来で、**切片・集計軸**になりうる論理列（または複合キー）の候補。004 が **`dimensions[]` に採用するか**を決める。 |
| measure 候補 | 003 の **value fields** 由来で、**集計・比較の対象**になりうる度量またはカウント対象の候補。004 が **`measures[]` に採用するか**を決める。 |
| grain | **1 論理行が表す観測単位**の宣言。006 上は **004 が意味正本**。 |
| time axis | **時間的な順序・間隔**を持つ軸。単なる「日付型の列」だけではなく、**系列・粒度・暦の意図**を含めて宣言しうる。 |
| category axis | **名義・階層ラベル**として切片・分類に**特に有効**な軸。**`dimensions[]` のサブセットへのマーカー**として宣言する（§category axis / filters）。 |
| filters | **分析上の安全な制約候補**（母集団・期間・除外規則等）。**画面の絞り込み UI 仕様ではない**。 |
| review point | 人が確認すべき**論点 1 条**。005 がキューに載せる単位。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) | 原本観測の正本。004 は**直接主入力にせず**、`trace_map` 経由で説明責任に用いる。 |
| [SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) | 判定の正本。`taxonomy_code`・`decision`・`evidence` を**補助入力**としてメタ制約・review に反映する。**004 は再判定しない**。 |
| [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) | **`NormalizedDataset` の正本**。**004 の主入力**。 |
| [SPEC-TI-005](SPEC-TI-005-human-review-flow.md) | **`review_required`／`review_points` の消費者**。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | `AnalysisMetadata` の必須フィールド正本。拡張は MINOR／Phase4。 |
| [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) | `taxonomy_code` 語彙。004 は語彙を増やさない。 |
| [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) | 見出し構造は 003 経由で間接参照。004 は見出しモデルを書き換えない。 |
| [SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) | 不確実性・特徴量の**消費者**（数式は 011）。 |
| [SPEC-TI-013](SPEC-TI-013-suggestion-generation.md) | 候補生成の**消費者**。004 は前提メタを渡す。 |

### 003 正規化結果との接続境界（MVP）

- **004 は** `rows[]`（論理行）、**`column_slots[]`**（列参照面）、**`trace_map[]`**（出典・不一致・未解決情報）を受け取り、必要に応じて **002／003 の trace を遡る**前提とする。  
- **003 出力を「意味確定済み」とはみなさない**。転記は **候補**であり、**semantic lock-in しない**（[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) §MVP 実装接続）。  
- **004** は dimension／measure／category_axis／time_axis 等を**候補として整理**し、`available_aggregations` や `review_points` の**前段**として扱う。**003 未解決事項を自動的に確定済み扱いしない**。  
- まだ **review 前提**の論点を **確定済み**として扱わない。**taxonomy**・**merges／多段見出し**由来の残りは **`review_points`**・**上位仕様**へ**委譲しうる**（005 はフロー正本、011 はスコア正本）。003 側の整理は **[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md)** の「004 分析メタデータへの受け渡し（MVP 境界）」を参照。

### 005 人確認フローへの受け渡し（MVP 境界）

- **`review_points[]`**（および **`review_required`**）を通じて **005** に **未解決**を渡す。**005** は必要に応じて 003 の **`trace_map[]`**、**`rows[]`**、**`column_slots[]`** を**参照**する前提とする（011／013 の正本責務を侵さない）。  
- **004** の整理結果を **「完全確定済み」**とはみなさない。**候補**整理・**review_points 化**までであり、**003／004 が抱え込まない未解決**を**閉じず**に **005** が受ける。  
- **人確認**が必要な論点は **005**／**上位仕様**へ**委譲**しうる。**004** は**勝手に確定済み扱いしない**。  
- 005 側の整理は **[SPEC-TI-005](SPEC-TI-005-human-review-flow.md)** の「004 分析メタデータとの接続境界（MVP）」を参照。

---

## 分析メタデータの位置づけ

パイプラインにおいて 004 は次に限定する。

1. **正規化結果の意味づけ**: 003 の論理行・列を **dimension／measure／grain** に写像する。  
2. **taxonomy 整合**: [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) に沿い **`grain` の説明**を一貫させる。  
3. **不確実性の顕在化**: 003 の `PARTIAL`／`FAILED`、002 の `NEEDS_REVIEW`／`ambiguity` 等を **`review_required`／`review_points`** および 011 向けヒントに落とす。  
4. **候補生成の土台**: 013 が **軸・許容集計・制約**を機械可読に扱えるよう宣言する。

**境界の再掲**: **001＝観測**、**002＝判定**、**003＝変換**、**004＝分析意味メタ**、**005＝人確認フロー**、**011＝信頼度**、**013＝候補生成**。

**人確認（005）に至る標準経路**: **`001 → 002 → 003 → 004 → 005`** である。**005 がキューの主入力とすべきシグナル**は **`AnalysisMetadata` の `review_required`／`review_points[]`** である。**002** の `NEEDS_REVIEW`、**003** の `PARTIAL`／`FAILED` 等は、**原則として本書の責務で `review_required`／`review_points[]` に落とす**（005 は **`review_points` を再生成する正本ではない**）。

---

## 入力

### 主入力（必須）

- **`NormalizedDataset`**（006 §5.7、[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) 準拠）  
  - `dataset_id`, `table_id`, `rows[]`, `trace_map`  
  - **任意** `dataset_payload.column_slots[]` — `rows[].values` の **`cN` と表列 index の対応**など 003 補助。**dimension／measure の確定入力ではない**（§dimensions／§measures との境界は 003／006 を参照）。  
- 各論理行の **key／value／metadata／source trace reference** の区分は **003 の定義に従う**。

### 補助入力（必須参照）

- **`JudgmentResult`**（006 §5.6、同一 `table_id`）  
  - **`taxonomy_code`**, **`decision`**, **`evidence[]`**（曖昧性・根拠）  
- 004 は **002 を上書きしない**。矛盾は **review／メタ注記**に記録する。

### 補助入力（推奨・003 副次）

- **`normalization_meta`**（003 の概念）: `normalization_status`, `skipped_regions[]`, `aggregate_rows[]`, `note_blocks[]`, `incomplete_bindings[]`, `type_normalization_notes[]`, `unit_application[]` 等。  
- **`HeadingTree`**（006 §5.5）: dimension の階層意味の補強に**参照のみ**（004 は木を改変しない）。

### 主入力に含めないもの

- **`TableReadArtifact` を 004 の主入力としない**。セル値・OCR 結果の再解釈は 001 の責務。004 は **003 出力と 002 参照**からメタを組み立てる。

### MVP 実装スパイク（003→004「参照のみ」）

本番の dimension／measure／grain 確定の前に、**003 が `dataset_payload` に載せた痕跡を 004 が読んだことを検証可能にする**ための最小接続を許容する。

- **読む対象**（[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の MVP 出力に準拠）: `normalization_input_hints`（002 evidence 由来のヒント）→ **`trace_map`**（003 の実行痕跡）→ **`rows[]`**（先頭行の `values` キー名など**要約プレビュー**に限る。セル値の再解釈はしない）→ 任意の **`column_slots[]`**（003 列カタログ。**`cN` と `table_column_index` の対照**。004 は **slot を `dimensions`／`measures` に昇格しない**）。
- **書き込み**: `AnalysisMetadata.decision` に観測サマリ（実装例: `mvp_dataset_input_observation`、`schema_ref`: `ti.mvp_004_dataset_input_observation.v1`）。**`column_slots_summary`** に例えば次を載せうる: **`read`**、**`entry_count`**、**`hints_from_002_present_count`**、**`slot_id_values_key_preview`**（先頭数件の `slot_id`／`values_key`／`has_hint_from_002`）。**`decision` 内の 004 本番ブロック（例: `block`）は置き換えない**。`review_points[]` に **参照のみ**を示す論点（例: `004-mvp-dataset-inputs-observed`、**`column_slots` が非空のとき** `004-mvp-column-slots-referenced`）を追加しうる。
- **禁止**: 本スパイクは **`semantic_lock_in` を付けない**（意味確定とみなさない）。**011 への特徴量化・013 への候補生成ロジックは追加しない**。`JudgmentResult` を 004 が**再読して上書き**する処理は本スパイクの範囲外（002 は引き続き補助入力の正本）。

---

## 出力

### 主成果物: `AnalysisMetadata`

[SPEC-TI-006 §5.8](../01_foundation/SPEC-TI-006-io-data.md) の必須フィールド（`metadata_id`, `dataset_id`, `grain`, `dimensions[]`, `measures[]`）を満たし、本書の各節で定める**意味**を載せる。

### 拡張プロパティ（006 MINOR／Phase4 で Schema 化）

| プロパティ（概念名） | 説明 |
|----------------------|------|
| `time_axis` | §time axis の定義 |
| `category_axes[]` | §category axis / filters |
| `filters[]` | 同上 |
| `available_aggregations[]` | §available aggregations |
| `inferred_business_meaning` | §inferred business meaning |
| `review_required` | §review_required |
| `review_points[]` | §review_points |
| `metadata_confidence_hints` | §011 への引き継ぎ（定性的） |

---

## AnalysisMetadata の原則

1. **非変換**: `NormalizedDataset` の行数・セル値を **004 で再計算しない**（003 正本）。  
2. **非再判定**: `taxonomy_code`・見出し採否を **変更しない**。矛盾は **review／フラグ**に記録。  
3. **意味単位**: 002 の列役割タグは**ヒント**とし、**dimension／measure として再ラベル**する（§dimensions／§measures）。  
4. **`grain` 一意の説明**: 同一 `AnalysisMetadata` 内で **1 行の意味**が矛盾なく説明できること。  
5. **trace 尊重**: dimension／measure の各要素に **003 `trace_map` への参照**を持たせうる。  
6. **無理な確定禁止**: **inferred** は推定であることを明示し、曖昧性は **`review_points`** または 011 向けヒントに載せる。  
7. **下流の正本を侵さない**: 人確認の進行・スコア計算・候補の並びは **005／011／013** に委譲する。

---

## dimensions の定義

- **ソース**: 主に 003 の **key fields**、**metadata** にある列役割・階層情報。  
- **dimension 候補**: 上記から **切片・集計軸として意味がある**列（または複合キー）。  
- **採否**: 002 の `COL_ATTRIBUTE` 等を**機械的に dimension 確定**としない。**分析上、軸として使う価値があるか**で選別する。  
- **複合キー**: 多段見出しが連結キーになる場合は、**1 logical dimension** または **複数 dimension** にマッピング（003 の出力形式に合わせる）。  
- **単位・通貨**: **measure 側**または `filters`／メタ注記で扱うことが多い（dimension に載せないことを推奨するケースが多い）。  
- **時系列**: 時間を表す列は §time axis と整合させ、**同一論理対象を矛盾する二重定義にしない**。  
- **`category_axes` との関係**: **`category_axes[]` は `dimensions[]` のサブセットを指すマーカー**。各 category axis は **必ず 1 つの dimension と対応**する。**すべての dimension が category axis になるとは限らない**（内部キー・連番など）。**純粋な時間軸**は `time_axis` 側を主とし、**category_axes に載せない**のが基本。

---

## measures の定義

- **ソース**: 主に 003 の **value fields**。  
- **measure 候補**: **数値・金額・比率・カウント対象**になりうる論理列。002 の `COL_MEASURE`・型・単位メタは**ヒント**。  
- **名義中心の表**: LOOKUP_MATRIX 等では「値」が名義でも **measure 相当にするか**、**count のみ**にするかは taxonomy と 013 の設計に委譲する。**measure を空**にし category 集約のみ許す構成もありうる。  
- **単位**: 003 の `unit_application[]` を **measure ごと**に紐づけ、**競合**は `review_points` に載せる。  
- **集計行**: **`aggregate_rows[]`** にある値は **通常、主分析の measures の母集団に含めない**。集計行の存在はメタで**別参照**しうる。

---

## grain の定義

**grain** は **1 論理行が何を 1 件として表すか**の宣言である。006 上 **004 が意味正本**。

| `taxonomy_code`（002／009 前提） | grain の捉え方（0.1 標準） |
|----------------------------------|----------------------------|
| `TI_TABLE_LIST_DETAIL` | **1 行＝1 レコード（1 観測エンティティ）**。 |
| `TI_TABLE_CROSSTAB`（縦持ち後） | **1 行＝1 交差セルの展開**。 |
| `TI_TABLE_TIME_SERIES` | **1 行＝1 時点（または期間）×系列**。ワイド保持なら **grain 説明に横持ちである旨**を明記する。 |
| `TI_TABLE_KEY_VALUE` | **1 行＝1 属性ペア**（縦長）または **1 行＝1 レコード**（ワイド）。003 の経路に合わせて明示。 |
| `TI_TABLE_UNKNOWN` または 003 `PARTIAL` | grain を**断定しない**、または **仮説 grain**＋`review_required=true`。 |

**measure／dimension との境界**: **grain は「行の単位」**であり、**列の意味（dimension／measure）を置き換えない**。集計の許容は §available aggregations で **grain と整合**させる。

---

## time axis の定義

- **単なる日付列ではない**: **粒度**（日／月／四半期等の**意図**）、**暦・会計期間の解釈**、**複数系列**の有無を **time axis 宣言**に載せうる。  
- **位置づけ**: 時間を表す列／論理フィールドは **`dimensions[]` にも現れうる**。同時に **`time_axis` を独立プロパティ**として、**粒度・系列対応**を集約しうる。  
- **二重定義の禁止**: **同一の時間論理フィールド**について、`dimensions[]` の説明と `time_axis` が**矛盾してはならない**（片方を正とし、参照 ID でリンク）。  
- **検出の手掛かり**: `COL_TIME`、日付・年月型、003 の TIME_SERIES 経路メタ。  
- **category との分離**: **同一列を time と category の両方に載せない**。境界が曖昧なら `review_points`。  
- **会計暦の最終解釈**: ビジネスルール／人確認（005）に残しうる。

---

## category axis / filters の定義

### category axis

- **定義**: **切片・分類・比較に特に有効**な **dimension のサブセット**へのマーカー。**すべての category axis は dimension でもある**。  
- **filters との違い**: **category axis は「軸」そのもの**（次元）。**filters は「その軸や他条件に対する制約・母集団の限定」**（分析上安全な既定範囲）。  
- **013 向け**: 軸として **drill-down・切片**に使う dimension を **明示**し、候補生成が **軸候補を機械的に列挙**できるようにする。  
- **time との分離**: **時間と名義を同一 dimension に混在させない**。曖昧なら `review_points`。

### filters

- **意味**: **分析上の安全な制約候補**。**画面の絞り込み操作の UI 仕様ではない**（007／014）。  
- **目的**: 誤解釈を減らす**母集団・期間・除外規則**を機械可読にする。  
- **ソース**: 003 の `normalization_status`、行種別、`aggregate_rows[]` 除外の既定、単位メタ、002 の `decision`。  
- **例**: **集計行は主分析から除外済み**の明示、**time_axis と整合する期間**、単位競合のある measure を**候補から外す**前提の宣言。  
- **`NEEDS_REVIEW`**: **filters を過度に強く絞り込まない**／**review とセット**を推奨。  
- **013 向け**: 候補の**母集団・前提**として `filters` を読み、**違反候補を出さない**材料にする（最終ロジックは 013）。

---

## available aggregations の定義

- **目的**: **どの measure にどの集計を許可しうるか**を宣言し、[SPEC-TI-013](SPEC-TI-013-suggestion-generation.md) が **許容集合の範囲内**で候補を組み立てられるようにする。  
- **入力**: measure の型、**grain**、003 の `normalization_status`、単位競合、`aggregate_rows[]` の扱い。

| 条件 | 載せうる集計（例） |
|------|---------------------|
| **数値 measure**（スカラー度量） | `sum`, `avg`, `min`, `max`, **行数 `count`** |
| **名義中心** | `count`, `distinct_count`（または同等）を中心に |
| **003 `PARTIAL`・単位競合・集計行を母集団に含める設計** | **`avg`／`sum` を外し `count` のみ**等、**抑制**しうる。理由は `review_points` またはメタ注記へ。 |

- **不適切な集計を避ける**: **grain と論理矛盾する aggregation は `available_aggregations` に載せない**（例: 交差セル grain に対し、意味の通らない再平均）。  
- **合計／平均／件数／構成比**: **構成比**は **分母の定義が grain・filters と整合するとき**に限り候補に含めうる。**分母が不明確**なら載せないか `review_points` へ。  
- **詳細アルゴリズム**: 013。004 は **許容集合の宣言**に留める。

---

## inferred business meaning の扱い

- **性質**: **推定**される業務ラベル・短い説明。**確定の業務定義ではない**。  
- **入力源**: 列名（論理列 ID／キャプション由来）、003 `unit_application[]`、002／009 の `taxonomy_code`、ドメイン辞書（将来・任意）。  
- **出してよい条件**: 列名・単位・taxonomy が**互いに矛盾が小さい**、**grain が仮説でも**弱いラベルに留められる場合。  
- **弱める／空にする条件**: **`review_required` が真**、**grain が仮説のまま**、**単位競合が強い**、003 **`PARTIAL`／`FAILED` が強い** → **空または弱いラベル**を優先し、011 向け **`metadata_confidence_hints`** を優先。  
- **用途**: 013 の候補優先度、説明生成、011 の文脈特徴量（**重み付けは 011**）。  
- **禁止**: データカタログ上の**正式定義**として単独で扱わない。

---

## review_required の判定方針

次のいずれかを満たすとき **`review_required = true`** とする（複数可）。

- 003 の `normalization_status` が **`PARTIAL`** または **`FAILED`**  
- `incomplete_bindings[]` または `skipped_regions[]` が**分析解釈に影響する**  
- 002 の `decision === NEEDS_REVIEW`、または `evidence` に **ambiguity**  
- 単位競合、003 `type_normalization_notes` に**大量の型パース失敗**  
- **grain** が仮説のまま、または断定不能

**004 は人確認を起動しない**。**フラグと論点の列挙**までが責務。起動条件の運用は 014 と整合させうる。

---

## review_points の生成方針

- **粒度**: **005 が `point_id` 単位でキューに載せられる**大きさ。**1 論点＝1 要素**を基本。  
- **構造（概念上の最小）**: `point_id`, `category`, `priority` または `severity`, `affected_fields`, `trace_refs`, `suggested_resolution_type`（005 が解消パスを選ぶヒント）。**JSON Schema の完全形は 006 Phase4**。  
- **003 信号の反映例**: `PARTIAL`→利用範囲の限定、`FAILED`→再正規化前提、`incomplete_bindings[]`→軸未確定、`skipped_regions[]`→対象外領域、`aggregate_rows[]`／`note_blocks[]`→主分析との合算注意。  
- **002 の competing 仮説**: **004 で打ち消さない**。**006 MINOR** の `competing_hypotheses` 等で保持しうる。  
- **不明は不明のまま**: **無理に完全確定せず** `review_points` に残す。

### `trace_refs`（座標参照と論理参照）

- **`trace_refs` が原本のセル／矩形を指す**ときは、**[SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) および [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) と同じ 0-based inclusive**（行・列の範囲含む）に従う。  
- **座標参照**と **論理フィールド ID・`dimensions[]`／`measures[]` 上のパス等**を**同一の表現に混在させない**。論理参照は**別種別または別表現**としうる。**参照の統一スキーマ**は **006 Phase4** に委譲するが、**幾何参照の基準は本書時点で上記に固定**する。

---

## 005 への引き継ぎ

- **渡すもの**: **`review_required`**, **`review_points[]`**（§review_points の構造）。**004 はフロー・質問文を定義しない**。  
- **役割分担**: 004 が **「何が不明か・どのフィールドに効くか・trace はどこか」**を構造化する。005 が **優先順位・セッション・再実行接続**の正本。  
- **PATCH 契約**: 人確認後の `AnalysisMetadata` 更新の**詳細手順**は 005／014 に委譲。004 は **更新されうるフィールドの意味**を本書で正本化する。  
- **暫定経路（非標準）**: **`AnalysisMetadata` が未生成**のとき、または **フェイルセーフ**として、オーケストレーション（**014**）が **002／003 の状態だけ**を根拠に人確認を起動しうる。**その経路は標準経路ではない**。**運用上は速やかに 004 を生成し `review_points` を主入力に戻す**ことを推奨する。

---

## 011 への引き継ぎ

- **渡すもの**: **`metadata_confidence_hints`**（定性的）、**`review_required`**, **`review_points[]` の有無・件数・category 分布**（特徴量化の素材）、003 由来の **正規化ステータス**、**inferred の強さ／空**の区別。  
- **004 がやらないこと**: **スコア式・閾値・重み**（011 正本）。  
- **一貫性**: **`review_required` が真**なのにスコアだけが高い、といった**矛盾**を避けるため、011 は 004 のフラグを**特徴量として読む**前提とする（合成規則は 011）。

---

## 013 への引き継ぎ

- **渡すもの**: **`dimensions[]`**, **`measures[]`**, **`grain`**, **`time_axis`**, **`category_axes[]`**, **`filters[]`**, **`available_aggregations[]`**, **`inferred_business_meaning`**（あれば）。  
- **004 がやらないこと**: **候補の並び・文言・抑制の最終ロジック**（013 正本）。  
- **制約**: 013 は **`available_aggregations` で宣言された集合を超える集計候補を出さない**前提とする。 **`filters` を母集団前提**として読む（§category axis / filters）。

---

## AnalysisMetadata の構造方針

| ブロック | 006 必須 | 主な入力（003） | 主な下流 |
|----------|----------|-----------------|----------|
| `metadata_id`, `dataset_id` | ✓ | `dataset_id` 対応 | 全下流 |
| `grain` | ✓ | 論理行の意味、taxonomy | 全下流 |
| `dimensions[]` | ✓ | key, metadata | 分析、013 |
| `measures[]` | ✓ | value, 単位 | 分析、013 |
| `time_axis` | 拡張 | 時間列、TIME_SERIES メタ | 時系列、filters、013 |
| `category_axes[]` | 拡張 | dimensions のサブセット | 切片、013 |
| `filters[]` | 拡張 | 正規化ステータス、行種別 | 013 |
| `available_aggregations[]` | 拡張 | measure 型、grain | 013 |
| `inferred_business_meaning` | 拡張 | 列名、単位、taxonomy | 013、011 |
| `review_required`, `review_points[]` | 拡張 | PARTIAL、002 ambiguity 等 | 005 |
| `metadata_confidence_hints` | 拡張 | 正規化・推定の弱さ | 011 |

**003 の key／value／metadata／trace の読み方**: **key**→dimensions／time／category 候補、**value**→measures／型、**metadata**→filters／aggregations 制約／011 素材、**trace**→各要素の原本説明。**`aggregate_rows[]`／`note_blocks[]`** は **通常 measures に混ぜず**、**review または説明コンテキスト**へ参照渡し。

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| 人確認フロー・質問・セッション | SPEC-TI-005 |
| 信頼度の式・閾値 | SPEC-TI-011 |
| 分析候補の生成・抑制・並び | SPEC-TI-013 |
| UI・文言 | SPEC-TI-007 |
| API・永続化 | SPEC-TI-014／015 |
| `AnalysisMetadata` の JSON Schema 完全形 | SPEC-TI-006 Phase4 |
| taxonomy・見出しの正本 | SPEC-TI-009／010／002 |
| 正規化アルゴリズム | SPEC-TI-003 |

---

## レビュー観点

- **003 を主入力**とし、**001 を主入力にしていない**ことが一貫しているか。  
- **dimension 候補／measure 候補／grain** の境界が矛盾していないか。  
- **time axis** が「日付列＝time」の単純化に落ちていないか。**category／filters** との違いが明確か。  
- **`available_aggregations` が grain・型・PARTIAL／単位と整合**しているか。  
- **`review_points[]` が 005 のキュー**として十分か（`point_id`・`trace_refs` 等）。  
- **011／013 への橋渡し**が 004 の責務を越えていないか。  
- 009 の語彙外ラベルを 004 が作っていないか。

---

## 初版成立ライン

- **`NormalizedDataset` を主入力**、`JudgmentResult` を補助、**001 を主入力にしない**方針が明記されている。  
- **`dimensions`／`measures`／`grain`／time／category／filters／available_aggregations／inferred／review_*** が**本文として定義**されている。  
- **`review_required`／`review_points`** の判定・生成と **005 への渡し方**が書かれている。  
- **011／013 への橋渡し**が**越権なく**書かれている。  
- **`AnalysisMetadata` の構造方針**と **001〜003／005／011／013** の境界が明確。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.2.5 | 2026-04-07 | §関連仕様書に「005 人確認フローへの受け渡し（MVP 境界）」を追記（review_points・003 参照・未解決の閉じない委譲・005 節への参照）。 |
| 0.2.4 | 2026-04-07 | §関連仕様書に「003 正規化結果との接続境界（MVP）」を追記（候補性・trace 遡及・review／上位委譲・003 節への参照）。 |
| 0.2.3 | 2026-04-03 | MVP 観測に `column_slots_summary` と `004-mvp-column-slots-referenced` を追記（参照のみ・意味確定なし）。 |
| 0.2.2 | 2026-04-03 | 主入力に任意 `column_slots[]` を追記（`cN` 橋渡し・004 非確定）。MVP 観測節に `column_slots` の位置づけを補足。 |
| 0.2.1 | 2026-04-03 | MVP: `dataset_payload` の `normalization_input_hints`／`trace_map`／`rows` を参照入力として要約し `decision`／`review_points` に観測痕跡を残すスパイク（意味確定なし）。 |
| 0.2 | 2026-04-19 | 005 への標準経路（001→002→003→004→005）、暫定トリガの位置づけ、`trace_refs` の 0-based inclusive と論理参照の区別。 |
| 0.1 | 2026-04-18 | Draft 初版本文。指定 25 章構成。003 主入力・002 補助・001 非主入力、軸／grain／集計／review／005・011・013 引き継ぎ、構造方針。 |
