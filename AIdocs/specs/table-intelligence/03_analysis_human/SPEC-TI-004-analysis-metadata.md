---
id: SPEC-TI-004
title: 分析メタデータ仕様書
status: Draft
version: 0.2
owners: []
last_updated: 2026-04-07
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-003, SPEC-TI-006, SPEC-TI-009, SPEC-TI-010]
---

## 文書目的

[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の `NormalizedDataset`（および 003 が付随させうる **正規化メタ**）を入力とし、**分析エンジン・人確認・信頼度・分析候補生成**が共通に参照できる **分析メタデータ（`AnalysisMetadata`）** を組み立てる規約を定義する。

**明記（責務の正本）**

- **[SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md)** は **原本観測**（セル・結合・座標）の**正本**。004 は Artifact を**改変しない**。説明・監査のために **003 の `trace_map` 経由**で参照する。  
- **[SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md)** は **判定**（`taxonomy_code`・見出し採否前提・行種別・列役割・`decision`／`evidence`）の**正本**。004 は **taxonomy を再判定しない**。**見出しの採否を再判定しない**（010 構造・002 evidence を前提とする）。  
- **[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md)** は **変換・正規化**の**正本**。004 は **変換そのものを行わない**（行の追加・縦持ちの再実行・型の再パースはしない）。  
- **本仕様（004）** は **`dimensions`／`measures`／`grain` の意味**および本書で定める **分析メタデータ全体の正本**である（[SPEC-TI-006 §5.8](../01_foundation/SPEC-TI-006-io-data.md) の必須フィールドと整合。拡張フィールドは **006 MINOR** または本書の推奨プロパティとして扱う）。  
- 004 は **`NormalizedDataset` の key／value／metadata／trace 区分**（003 の定義）を**読み取り前提**に、**分析上の意味単位**へマッピングする。  
- **[SPEC-TI-005](SPEC-TI-005-human-review-flow.md)** へは **`review_required`／`review_points`** を**構造化して**渡せること（画面・文言は 005／007）。  
- **[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)** へは **メタデータ上の不確実性・曖昧性**（欠落軸、部分データ、単位競合等）を**特徴量として**渡せること（数式は 011）。  
- **[SPEC-TI-013](SPEC-TI-013-suggestion-generation.md)** へは **suggested analyses** の**前提となる metadata**（利用可能集計、軸、制約）を渡すこと（候補の生成・抑制ロジック自体は 013）。

---

## スコープ

- `NormalizedDataset` から **分析メタデータを組み立てる方針**と**優先順位**
- **`dimensions`／`measures` の定義方針**（002 の列役割タグを**そのまま採用するのではなく**、分析上の意味単位へ整形）
- **`grain` の定義方針**（1 論理行の意味の**明示**；taxonomy ごとの表現の揃え）
- **time axis**／**category axis** の識別と宣言
- **filters**（分析前に適用可能な制約の宣言）
- **available aggregations**（データと grain に整合する集計の許容集合）
- **inferred business meaning**（推定される業務上の意味・注意書き）
- **`review_required`／`review_points`** の生成方針
- **003 の PARTIAL／FAILED／`incomplete_bindings`／`skipped_regions` 等**と **人確認・信頼度**の接続
- **`aggregate_rows[]`／`note_blocks[]`**（003 の概念）をメタデータ上で**どう参照するか**

---

## 非スコープ

以下は**詳細確定しすぎない**。委譲先を明記する。

- **読取ロジック**（001）・**判定ロジック**（002）・**正規化変換ロジック**（003）  
- **UI 表示**・利用者向け文言（[SPEC-TI-007](../05_experience_quality/SPEC-TI-007-ui.md)）  
- **HTTP**・**ジョブ API**（[SPEC-TI-014](../04_system/SPEC-TI-014-api.md)）  
- **DB 物理設計**（[SPEC-TI-015](../04_system/SPEC-TI-015-db.md)）  
- **分析候補生成アルゴリズムそのもの**（[SPEC-TI-013](SPEC-TI-013-suggestion-generation.md)）  
- **人確認 UI** のステップ文言・フロー詳細（[SPEC-TI-005](SPEC-TI-005-human-review-flow.md)）  
- **信頼度の数式**・閾値（[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)）

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 分析メタデータ | [SPEC-TI-006 §5.8](../01_foundation/SPEC-TI-006-io-data.md) の `AnalysisMetadata` および本書が推奨する**拡張プロパティ**の総称。 |
| dimension | 分析で**切片・集計軸**になる属性。003 の **key fields** およびメタから**意味単位**として選ばれる列（または複合キー）。 |
| measure | 分析で**集計・比較の対象**になる度量またはカウント対象。主に **value fields** 由来。 |
| grain | **1 論理行が表す観測単位**の宣言（006 上は 004 が意味正本）。 |
| time axis | **時間的な順序・間隔**を持つ軸。**次元としては dimension の特別扱い**（§time axis）。メタ上は**独立プロパティ `time_axis` としても宣言**しうる。 |
| category axis | **名義・階層ラベル**として切片・分類・比較に**特に有効**な軸。**`dimensions` のサブセットとして選ばれたマーカー**（§category axis／§dimensions との関係）。 |
| inferred business meaning | 列名・単位・ドメイン辞書から**推定**される業務説明。**確定事実ではない**旨をメタに付す。 |
| review point | 人が確認すべき**論点の 1 条**（理由コード・参照 trace・優先度を持ちうる）。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) | 原本。**004 は直接は読まず**、`trace_map` 経由の説明責任に用いる。 |
| [SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) | 判定の参照。`taxonomy_code`・`decision`・`evidence`（曖昧性）は **メタの制約・review** に反映するが**再判定しない**。 |
| [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) | **直接入力正本**（`NormalizedDataset`）。key／value／metadata／trace の区分と正規化メタを消費する。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | `AnalysisMetadata` の必須フィールド（`metadata_id`, `dataset_id`, `grain`, `dimensions[]`, `measures[]`）の正本。拡張は MINOR。 |
| [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) | `taxonomy_code` の語彙。**004 は語彙を増やさない**。grain・軸の期待を**参照**する。 |
| [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) | 見出しと binding の構造理解に**間接**に依存（003 経由）。004 は見出しモデルを**書き換えない**。 |
| SPEC-TI-005 | `review_required`／`review_points` の**消費者**。 |
| SPEC-TI-011 | 不確実性・曖昧性の**消費者**。 |
| SPEC-TI-013 | `available aggregations` 等を**前提**に候補を生成。 |

---

## 分析メタデータの位置づけ

表解析パイプラインにおいて、004 は次に限定する。

1. **正規化結果の意味づけ**: 003 の論理行・列を **分析の言葉**（dimension／measure／grain）に写像する。  
2. **taxonomy 整合**: [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) のタイプに応じ、**grain の説明**を**ぶれない形**で宣言する（§grain）。  
3. **不確実性の顕在化**: 003 の `PARTIAL`／`FAILED`・欠落 binding 等を **`review_required`／`review_points`** および 011 向けフラグに落とす。  
4. **候補生成の土台**: 013 が **利用可能集計・軸**を機械可読に扱えるよう **`available aggregations` 等**を宣言する。  

**境界の再掲**: **001＝観測**、**002＝判定**、**003＝変換**、**004＝意味メタデータ**、**013＝候補生成**。

---

## 入力

### 必須

- **`NormalizedDataset`**（006 §5.7、[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) 準拠）  
  - `dataset_id`, `table_id`, `rows[]`, `trace_map`  
- **`JudgmentResult`**（006 §5.6）の参照（同一 `table_id`）。**`taxonomy_code`・`decision`・`evidence[]`** をメタ制約・review に用いる。  
- **003 の論理区分の理解**: 各論理行は [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の「`rows[]` の論理要素」に従い **key／value／metadata／source trace reference** を含みうる。

### 推奨（あれば利用）

- **`normalization_meta`**（003 の副次成果物）: `normalization_status`, `skipped_regions[]`, `aggregate_rows[]`, `note_blocks[]`, `incomplete_bindings[]`, `type_normalization_notes[]`, `unit_application[]` 等。  
- **`HeadingTree`**（006 §5.5）: dimension の**階層意味**の補強に**参照のみ**（004 は木を改変しない）。

---

## 出力

### 主成果物: `AnalysisMetadata`

[SPEC-TI-006 §5.8](../01_foundation/SPEC-TI-006-io-data.md) の必須フィールドを満たし、本書で定める**意味**を載せる。

| フィールド（006 必須） | 004 における意味 |
|------------------------|-------------------|
| `metadata_id` | 一意 ID。 |
| `dataset_id` | 入力 `NormalizedDataset` と対応。 |
| `grain` | **1 論理行の意味**の宣言（§grain）。 |
| `dimensions[]` | 分析軸（§dimensions）。 |
| `measures[]` | 度量・分析対象値（§measures）。 |

### 本書が推奨する拡張（006 MINOR で正式化）

初版では **006 を壊さない**ため、次を **`AnalysisMetadata` の拡張**または **別オブジェクト参照**として載せうる。

| プロパティ（概念名） | 説明 |
|----------------------|------|
| `time_axis` | §time axis。単一または複数の時間軸宣言。 |
| `category_axes[]` | §category axis。名義軸（複数可）。 |
| `filters[]` | §filters。適用可能な既定フィルタ候補。 |
| `available_aggregations[]` | §available aggregations。 |
| `inferred_business_meaning` | §inferred business meaning。 |
| `review_required` | §review_required／review_points。boolean または列挙。 |
| `review_points[]` | 人確認の論点リスト。 |
| `metadata_confidence_hints` | 011 への**定性的**ヒント（数式は 011）。 |

---

## 分析メタデータの原則

1. **非変換**: `rows[]` の行数・列値を **004 で再計算しない**（003 正本）。  
2. **非再判定**: `taxonomy_code`・見出し採否を**変更しない**。矛盾は **review／flags** に記録。  
3. **意味単位**: 002 の `COL_*` タグは**ヒント**とし、**dimension／measure として再ラベル**する（§dimensions／§measures）。  
4. **grain 一意の説明**: 同一 `AnalysisMetadata` 内で **1 行の意味**が**矛盾なく説明できる**こと（§grain）。  
5. **trace 尊重**: dimension／measure の各要素に **003 `trace_map` への参照**を持たせうる（006 Phase4 でフィールド固定）。  
6. **無理な確定禁止**: **inferred** は推定であることを明示し、**曖昧性**は `review_points` または 011 へ。

---

## metadata 構成要素一覧

| 構成要素 | 主な入力（003） | 主な出力先 |
|----------|-----------------|------------|
| dimensions | key fields、metadata（列役割）、category／time の判定 | 分析クエリ、013 |
| measures | value fields、単位メタ | 分析クエリ、013 |
| grain | 論理行の意味、taxonomy | 全下流 |
| time_axis | `COL_TIME`、日付型、TIME_SERIES 経路。**dimension 上の時間と同一対象を二重定義しない**（§time axis） | 時系列分析、filters |
| category_axes | **dimensions のうち**切片・分類に特化してタグ付けしたサブセット（§dimensions との関係） | 切片、drill-down、013 |
| filters | **分析上の安全な制約候補**（§filters）。**画面の絞り込み UI 仕様ではない** | 013、（UI は 007／API は 014 が投影） |
| available_aggregations | measure の型・grain | 013 |
| inferred_business_meaning | 列名・単位・taxonomy・辞書（将来） | 013 優先度、011 特徴量（§inferred business meaning） |
| review_required／review_points | PARTIAL、欠落、002 ambiguity | 005 |
| 不確実性フラグ | normalization_meta、型ノート | 011 |

---

## dimensions の定義方針

- **ソース**: 主に 003 の **key fields**、および **metadata** にある列役割・階層情報。  
- **分析単位**: 002 の `COL_ATTRIBUTE` 等を**自動的に dimension 確定**としない。**切片に使う意味があるか**で選別する。  
- **複合キー**: LIST_DETAIL で多段見出しが**連結キー**になっている場合は、**1 つの logical dimension**（セグメント付き）または **複数 dimension**（個別列）にマッピング（003 の出力形式に合わせる）。  
- **単位・通貨**: **dimension ではなく** measure 側または `filters`／メタ注記で扱うことが多い（**暫定**）。  
- **時系列**: 時間軸の扱いは §time axis。**同一の時間対象を dimension と `time_axis` で矛盾して二重定義しない**。

### dimensions と category_axes の関係（Draft 0.2 暫定標準）

- **`category_axes[]` は `dimensions[]` のサブセットを指すマーカー**である。すなわち、**各 category_axis は必ず 1 つの dimension と対応**し、その dimension は「切片・分類・比較に**特に有効**」である旨を**タグ付け**したものとして宣言する（JSON Schema の表現は Phase4）。  
- **すべての category_axis は dimension でもある**（＝分析可能な軸として `dimensions[]` に含まれる）。  
- **逆に、すべての dimension が category_axis になるとは限らない**。例: **行 ID・連番・内部キー**は slice に向かないことが多く **category_axis に選ばない**。**純粋な時間軸**（`time_axis` に寄せる）は **category_axes には含めず** `time_axis` 側で扱うのが基本（§time axis）。**単位のみが付いた補助列**は measure／メタ側に寄せ、**category_axis にしない**ことが多い（暫定）。

---

## measures の定義方針

- **ソース**: 主に 003 の **value fields**。`COL_MEASURE`・型・単位メタを**ヒント**とする。  
- **カテゴリ値**: LOOKUP_MATRIX 等では「値」が名義でも **measure 相当**として扱うか、**count 専用**にするかは taxonomy と 013 で調整（**暫定**: 名義のみなら **measure 空**＋category 集約のみ可、を許容）。  
- **単位**: `unit_application[]`（003）を **measure ごと**に紐づけ、**競合**は `review_points` に載せる。  
- **集計行**: **`aggregate_rows[]`** にある値は **通常 measures の母集団に含めない**（別途「集計メタとしての参照」フラグを付けうる）。主分析は **明細 `rows[]`** を正とする。

---

## grain の定義方針

`grain` は [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) 上 **004 が意味正本**。**1 論理行＝何の 1 観測か**を**文章または構造化オブジェクト**で宣言する（JSON Schema は Phase4）。

| taxonomy（002／009 前提） | grain の捉え方（暫定標準） |
|---------------------------|----------------------------|
| `TI_TABLE_LIST_DETAIL` | **1 行＝1 レコード（1 観測エンティティ）**。多段見出しは dimension の合成に過ぎない。 |
| `TI_TABLE_CROSSTAB`（縦持ち後） | **1 行＝1 交差セルの展開**（行軸キー×列軸キーで特定される度量）。 |
| `TI_TABLE_TIME_SERIES` | **1 行＝1 時点（または期間）×系列の観測**。**ワイド保持**の場合は「1 行＝複数時点を横断」となりうるため、**grain 説明に「横持ちワイド」を明記**する。 |
| `TI_TABLE_KEY_VALUE` | **1 行＝1 属性ペア**（縦長）または **1 行＝1 レコード全体**（ワイド 1 行）。003 の経路に合わせて**明示**。 |
| `TI_TABLE_UNKNOWN`／`PARTIAL` | grain を**断定しない**か、**仮 grain**＋`review_required=true` を推奨。 |

---

## time axis の定義方針

- **位置づけ（Draft 0.2 暫定標準）**: **`time_axis` は dimension の特別扱い**である。時間を表す列／論理フィールドは、**原則として `dimensions[]` にも現れうる**（時間をキーとする分析のため）。同時に、メタデータ上は **`time_axis` を独立プロパティとして宣言可能**とし、**粒度・暦の意図・系列の対応**をここに集約しうる。  
- **二重定義の禁止**: **同一の時間列（論理フィールド）について**、`dimensions[]` の説明と `time_axis` の説明が**矛盾してはならない**（片方を正とし、他方は参照 ID でリンク）。  
- **検出**: `COL_TIME`、日付・年月型の value／key、003 の TIME_SERIES 経路メタ。  
- **宣言**: `time_axis` に **列 ID または論理フィールド ID**、**粒度**（日／月／四半期等の**意図**。確定はビジネスカレンダーは別）、**複数系列**の有無を載せる。  
- **ワイド TIME_SERIES**: 複数時間列がある場合は **複数 series** または **縦持ち後の単一 time dimension** のどちらかに**論理統一**を図る（003 と矛盾させない）。  
- **category_axes との併存（基本方針）**: **時間軸（time）と名義軸（category）は直交しうる**。同一列を **time と category の両方に載せない**。曖昧なら `review_points`。  
- **委譲**: 会計期間・暦のずれの**最終解釈**はビジネスルール／人確認（005）に残しうる。

---

## category axis の定義方針

- **定義**: **category_axes は dimensions のうち、切片・分類・比較に特に有効な軸のサブセット**（§dimensions との関係）。**すべての category_axis は dimension でもある**。  
- **検出**: 名義・階層ラベルとなる dimensions（地域・製品など）。003 の **多段 key** がそのまま階層になりうる。  
- **time との分離**: **時間と名義を同一 dimension に混在させない**（暫定）。境界が曖昧なら `review_points`。  
- **LOOKUP_MATRIX**: 交差の片側が記号・カテゴリの場合、**category_axes** を主とし、measure は空でもよい（013 で候補抑制）。

---

## filters の定義方針

- **意味（Draft 0.2）**: 本書の **`filters` は「分析上の安全な制約候補」**であり、**画面の絞り込み操作そのものの仕様ではない**（画面・API は 007／014）。**004 は「このデータを分析するときに、既定で守るべき／許容される範囲」をメタとして宣言する**。  
- **目的**: 誤解釈を減らすための**分析制約**（母集団・期間・単位整合・切片の許容値）を機械可読にする。  
- **ソース**: 003 の `normalization_status`、行種別メタ、**集計行除外**の既定、単位メタ、002 の `decision`。  
- **例（暫定）**: **集計行は主分析から除外済み**であることの明示、**対象期間**（time_axis と整合する範囲）、**単位競合がない measure のみ**を対象とする範囲、**有効な category 値の候補**（欠損多めの値は除外フラグ）。  
- **002 `decision`**: `NEEDS_REVIEW` の場合は **filters を強く絞り込みすぎない**／**review** とセット、を推奨。

---

## available aggregations の定義方針

- **目的**: [SPEC-TI-013](SPEC-TI-013-suggestion-generation.md) が **許容集合**を機械的に読み、候補を組み立てられるようにする（**並び・文言・抑制の最終ロジックは 013**）。  
- **入力**: measure の型（数値・名義など）、grain、003 の `normalization_status`、単位競合、`aggregate_rows[]` の扱い。  

### 最低限の決定基準（Draft 0.2 暫定）

| 条件 | `available_aggregations` に載せうる候補（例） |
|------|-----------------------------------------------|
| **数値 measure**（スカラー型の度量） | **`sum`**, **`avg`**, **`min`**, **`max`**, **`count`**（行数）を**原則候補**としうる。 |
| **名義中心**（カテゴリ・記号が主で数値が従属／不在に近い） | **`count`**, **`distinct_count`**（または同等の「ユニーク数」）を**中心候補**としうる。 |
| **003 `PARTIAL`**、**単位競合**、**集計行（`aggregate_rows[]`）を主分析に含める設計** | **一部 aggregation を抑制**しうる（例: `avg`／`sum` を外し `count` のみ、など）。理由は `review_points` またはメタ注記に。 |
| **grain と矛盾** | **その aggregation は宣言しない**（例: grain が「1 交差セル」なのに「再集計で平均を取る」等が論理破綻する場合）。 |

- **再明記**: **grain より細かい／矛盾する aggregation は `available_aggregations` に載せない**。013 は **004 が宣言した集合の範囲内**で候補を組み立てる前提とする。  
- **詳細アルゴリズム**: 013。004 は **許容集合の前提**の整理に留める。

---

## inferred business meaning の定義方針

- **内容**: **推定**される業務ラベル・短い説明。**確定の業務定義ではない**。  
- **主な入力源（優先度は実装で調整可）**: **列名**（論理列 ID／見出しキャプション由来）、**単位**（003 `unit_application[]`）、**taxonomy**（002／009）、**ドメイン辞書**（将来・任意）。  
- **推定を「出してよい」条件（暫定）**: 列名・単位・taxonomy が**互いに矛盾しない**程度に揃い、**grain が仮説でも**軽いラベル（「売上らしき」等）に**留められる**場合。  
- **推定を弱める／出さない方がよい条件（暫定）**: **`review_required` が高い**、**grain が仮説のまま**（断定できない）、**単位競合が強い**、003 の **`PARTIAL`／`FAILED` が強い**（データ欠落が支配的）。この場合は **空／弱いラベル**＋**011 向け uncertainty** を優先。  
- **用途**: 013 の**候補優先度付け**、説明生成、011 の文脈特徴量（**重みは 011**）。  
- **禁止**: **確定業務定義**として単独で扱わない（正式はデータカタログ／人確認）。

---

## review_required／review_points の定義方針

### `review_required`

次のいずれかで **true 推奨**（暫定）。

- 003 の `normalization_status` が `PARTIAL` または `FAILED`  
- `incomplete_bindings[]`／`skipped_regions[]` が**分析に影響する**  
- 002 の `decision === NEEDS_REVIEW` または `evidence` に **ambiguity**  
- 単位競合・型パース大量失敗（003 `type_normalization_notes`）  
- **grain** が仮説のまま

### `review_points[]`

**Phase4 の JSON Schema までは固定しない**が、**005 がそのまま列挙・優先付けできる**粒度で揃える（Draft 0.2）。

各要素は**概念上**、少なくとも次を持ちうる。

| 構成要素（概念名） | 説明 |
|--------------------|------|
| `point_id` | 論点の一意 ID（UUID 等。005 のトラッキング用）。 |
| `category` | 理由カテゴリ（例: `BINDING_INCOMPLETE`, `UNIT_CONFLICT`, `GRAIN_HYPOTHESIS`, `NORMALIZATION_PARTIAL`）。 |
| `priority` または `severity` | 対応優先度（数値または enum）。005 のキュー順に使う。 |
| `affected_fields` | 影響を受ける論理列 ID・measure ID・dimension ID のリスト。 |
| `trace_refs` | 003 `trace_map` または 001 座標への**参照**（監査・画面提示）。 |
| `suggested_resolution_type` | 解消の型（例: `HUMAN_CHOICE_AXIS`, `RE_READ`, `ACCEPT_PARTIAL`）。**具体手順は 005**。 |

| 003 の信号 | review への反映（例） |
|-------------|-------------------------|
| `PARTIAL` | 「一部領域のみ有効」「欠落 binding の列挙」 |
| `FAILED` | 「メタ生成は最小限」「再正規化前提」 |
| `incomplete_bindings[]` | 「該当セルは軸未確定」 |
| `skipped_regions[]` | 「対象外領域あり」 |
| `aggregate_rows[]`／`note_blocks[]` | 「集計／注記は別メタ。主分析との合算注意」 |

**無理に完全確定しない**: **不明は不明**として `review_points` に残す。

---

## 曖昧性の保持方針

- 002 の **複数仮説**（`evidence.details`）は **004 で打ち消さない**。**dimensions 候補の competing_hypotheses** 等（006 MINOR）で保持しうる。  
- 003 の **PARTIAL** は **「利用可能だが限定的」** を `metadata_confidence_hints` および 011 に伝える。  
- **001／002／003 との矛盾**は **新たな事実を捏造せず**、**review／flags** に記録。

---

## 003 の key／value／metadata／trace の読み方

| 003 区分 | 004 での主な利用 |
|----------|-------------------|
| key fields | dimensions／time_axis／category_axes の**主ソース** |
| value fields | measures／型制約 |
| metadata fields | filters、**review**、aggregations の制約、011 特徴量 |
| source trace reference | 各 dimension／measure 要素の **原本への説明責任** |

### `aggregate_rows[]`／`note_blocks[]`（概念）

- **`aggregate_rows[]`**: **主分析の measures の母集団からは通常除外**するが、**「集計行として存在」**を `inferred_business_meaning` または **別サブリソース参照**で記録し、**rollup 候補**（available_aggregations）と**矛盾しない**よう宣言する。  
- **`note_blocks[]`**: **dimensions／measures には載せない**。**review_points** または **説明コンテキスト**（013・説明生成）へ**参照渡し**。

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| 人確認フロー・質問・PATCH | SPEC-TI-005 |
| 信頼度の式・閾値 | SPEC-TI-011 |
| 分析候補の生成・抑制・並び | SPEC-TI-013 |
| UI 表示・文言 | SPEC-TI-007 |
| API・永続化 | SPEC-TI-014／015 |
| `AnalysisMetadata` の JSON Schema 完全形 | SPEC-TI-006 Phase4 |

---

## レビュー観点

- **grain** が taxonomy と**矛盾していない**か。  
- dimensions／measures が **003 の key／value と対応付け可能**か（無い列を捏造していないか）。  
- **`category_axes` が `dimensions` のサブセット**として一貫しているか（**孤立した category** がないか）。  
- **`time_axis` と dimension／`category_axes` が二重定義・混線していない**か。  
- **`filters` が分析制約として**読めるか（**UI 仕様と誤読されない**か）。  
- **`available_aggregations` が grain・型・PARTIAL／単位条件と整合**しているか。  
- **`aggregate_rows[]`／`note_blocks[]`** を誤って **通常 measures に混ぜていない**か。  
- **`review_points[]` に `point_id`／`trace_refs` 等の最小構成**が載りうるか（005 連携）。  
- 009 の語彙外のラベルを **004 が作っていない**か。

---

## 初版成立ライン

- 入力が **`NormalizedDataset`＋`JudgmentResult` 参照**に限定される**方針**が述べられている。  
- **`grain`・dimensions・measures** の定義方針が文章化されている。  
- **time／category／filters／available_aggregations／inferred_business_meaning／review_*** が**箇条書き以上**で定義されている。  
- **001／002／003／013／005／011** との境界が明確。  
- **003 の論理区分**との接続が説明されている。

**Draft 0.2 追加確認**: **dimensions／category_axes／time_axis の関係**、**filters＝分析制約**、**aggregations の最低基準**、**inferred の入力源と抑制**、**review_points の最小構造**が参照できること。

---

## 補足メモ（初版の外枠）

### この初版で未確定の論点（Draft 0.2 時点）

- `AnalysisMetadata` 拡張フィールドの **006 への正式取り込み**順序。  
- **複数 time_axis**（週と月の併存）の**禁止組合せ**ルール。  
- **domain 辞書**の有無と `inferred_business_meaning` の精度責任分界。  
- **ワイド TIME_SERIES** を **縦持ち相当の grain** に**正規化表現**だけで揃えるか、**専用フラグ**で許容するか。

### SPEC-TI-005 に引き継ぐ事項

- `review_points[]` の **`point_id`／`priority|severity`／`suggested_resolution_type`** を **UI キューとどう対応**させるか。  
- **`trace_refs` を画面でどう提示するか**（原本へのリンク）。  
- **人確認で dimension を差し替えた場合**の `AnalysisMetadata` 更新契約。

### SPEC-TI-011 に引き継ぐ事項

- `metadata_confidence_hints` と **正規化由来特徴量**の**合成**ルール。  
- **review_required** と **自動スコア**の一貫性。  
- **inferred_business_meaning** が弱い／空のときの **uncertainty 特徴量**（§inferred business meaning の抑制条件と連動）。

### SPEC-TI-013 に引き継ぐ事項

- 004 が宣言した **`available_aggregations` 許容集合**を**超えない**候補生成。  
- **`filters`（分析制約）**を**候補の母集団・前提**としてどう使うか。  
- **inferred_business_meaning** の**優先度付け**への利用（弱い推定の抑制）。

### SPEC-TI-001／002／003／006／009／010 との自己点検結果

| 観点 | 結果 |
|------|------|
| 001 | **整合**。観測を改変せず、trace 経由の説明のみ。 |
| 002 | **整合**。taxonomy・見出し採否を再判定しない。 |
| 003 | **整合**。変換を再実行せず、論理区分を消費するのみ。 |
| 006 | **整合**。必須フィールドを尊重し、拡張は MINOR 明記。 |
| 009 | **整合**。語彙を増やさず、タイプ期待に沿って grain を宣言。 |
| 010 | **整合**。見出しモデルを正本として書き換えない。 |

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.2 | 2026-04-07 | dimensions／category_axes／time_axis の関係、filters＝分析制約、aggregations 最低基準、inferred の入力と抑制、review_points 最小構造、005／011／013 粒度整合。 |
| 0.1 | 2026-04-06 | 初版本文。意味メタ正本、003 接続、grain／軸／集計／推定／review、005／011／013 前提。 |
