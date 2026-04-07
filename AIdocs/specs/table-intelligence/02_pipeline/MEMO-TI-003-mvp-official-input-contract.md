---
id: MEMO-TI-003-MVP-INPUT
title: 003 MVP 公式入力契約メモ（現行実装固定）
status: memo
version: 0.1.0
last_updated: 2026-04-07
depends_on: [SPEC-TI-003]
---

本メモは **現行 backend MVP スタブ**（`build_mvp_rows_and_trace_map_from_hints` 経由）に限定し、[SPEC-TI-003](SPEC-TI-003-normalization.md) の「理想の 003 入力」（001 全体・002 全体・taxonomy 経路選択等）との差を明示する。**本書は SPEC の正本を置き換えない**。

---

## 1. 参照した実装 / 仕様

| 種別 | パス / 文書 |
|------|-------------|
| 実装 | `backend/table_intelligence/normalization_hints.py`（`read_normalization_input_hints_from_dataset_payload`, `build_mvp_rows_and_trace_map_from_hints`, `_build_mvp_column_slots`） |
| 呼び出し | `backend/table_intelligence/services.py`（`_apply_judgment_hints_to_normalized_dataset`） |
| 仕様（MVP 接続の記述） | [SPEC-TI-003 § MVP 実装接続](SPEC-TI-003-normalization.md)（`normalization_input_hints` → `rows[]` / `trace_map` / `column_slots[]`） |
| 下流参照（観測のみ） | `backend/table_intelligence/mvp_004_dataset_inputs.py`（004 は 003 出力を**参照要約**するが意味確定しない） |

**003 MVP は何を読む実装か（一文）**  
現行 MVP では、**主入力として `dataset_payload.normalization_input_hints` を読み**、データ行のセル値は **001 由来の `TableReadArtifact.cells` から `raw_display` を転記**し、**`by_row_index` が空のときのみ**行 index 列挙のために **`TableScope.row_min` / `row_max`** を参照する。

---

## 2. 003 の公式入力一覧（MVP）

| 入力 | 経路・フィールド | MVP での役割 |
|------|------------------|--------------|
| 正規化入力ヒント | `NormalizedDataset.dataset_payload.normalization_input_hints` | **主消費**。`by_row_index` / `by_column_index`（002 J2-ROW / J2-COL 由来の**候補**）とメタ（`intent`, `schema_ref`, `source` 等）。 |
| セル観測 | 同一テーブル最新 `TableReadArtifact.cells` | **転記のみ**。`_sparse_cells_by_column_in_row` で `r`/`c` または `R{r}C{c}` キーにマッチするセルの **`raw_display`** を `rows[].values["c{N}"]` に載せる。 |
| 表スコープ（行範囲） | `TableScope`（`row_min`, `row_max`） | **`by_row_index` が空のときのみ**、走査する `table_row_index` の候補レンジを決める。 |

**現段階で MVP スタブが `build_mvp_rows_and_trace_map_from_hints` 内で直接読まないもの（例）**

- `merges`、`bbox`、001 のその他フィールド
- `JudgmentResult` の **`taxonomy_code` / `decision` / evidence 全体**（materialize 側でヒント dict に**既に畳まれた後**の `normalization_input_hints` のみがスタブに渡る）
- 004 の `dimensions` / `measures`、taxonomy 正本（009）への直参照

---

## 3. 003 が前提にしてよいこと / いけないこと

### 前提にしてよいこと

- **Index ベース**の行・列ヒント（`by_row_index` / `by_column_index` のキーは **0-based** の table 行・列 index として扱う実装）。
- **`cells` の `raw_display`** を文字列化して転記すること（欠損は空文字に落とす）。観測を**型変換・意味解釈で上書きしない**方針に沿う。
- **`TableScope.row_min` / `row_max`** による行レンジ（`by_row_index` 欠如時のフォールバック）。
- 出力側で **`semantic_lock_in: false`** を付与し、004 の意味確定と切り離すこと。

### 前提にしてはいけないこと

- **J2-COL（`by_column_index` の値）を列の意味確定ラベル**として扱うこと（実装・trace の `note` どおり **候補 / ヒント**）。
- **taxonomy 未連携のまま** `column_slots` や trace を **dimensions/measures への確定**として扱うこと。
- **evidence 全体を暗黙に再解釈**し、スタブ内で新たな判定を足すこと（002 の evidence は materialize でヒント抽出されるまで。スタブは **畳まれた `normalization_input_hints` のみ**を契約入力とする）。
- **`merges` 解釈済み**や**論理ヘッダグループ確定**を、現 MVP の入力として仮定すること。

---

## 4. 003 の出力契約（MVP）

成果物は `NormalizedDataset.dataset_payload` 上のフィールドとして materialize が書き込む。

### `rows[]`

- **表すもの**: ヒントにより「データ行」と扱った行の、**001 観測の転記結果**（`values` のキーは当面 **`c{N}`**）。`logical_row_index` / `table_row_index` / `mvp_stub` / `normalization_hint.from_002_row_kind` 等の**トレース補助**。
- **表さないもの**: 型正規化の確定、measure/attribute の**意味確定**、縦持ち後の論理 grain、002/004 の決定の置き換え。

### `trace_map[]`

- **表すもの**: スキップ行・列ヒント・セル転記などの**説明責任**（`trace_ref`, `kind`, `table_row_index` / `table_column_index`, `note`）。
- **表さないもの**: 完全な監査ログ、004/011 向けの**確定リスク評価**、evidence の再構成。

### `column_slots[]`

- **表すないもの**: dimension/measure の**カタログ確定**（docstring: 列カタログ／参照面）。`slot_id`, `table_column_index`, `values_key`, 任意の `hint_from_002`, `trace_kind_preview`, `trace_ref_ids`。集合は **`by_column_index` のキー ∪ 転記された `cN` 列**（taxonomy 非依存）。
- **表さないもの**: taxonomy コード確定、結合セル展開後の論理列、004 への自動昇格。

### `mvp_normalization_stub`（メタ）

- **表すもの**: スタブのスキーマ参照・件数サマリ（`schema_ref`, `column_slots_schema_ref`, 各種 count）。
- **表さないもの**: 正規化パイプライン全体のステータス正本（将来 `normalization_status` 等は SPEC-TI-003 / 006 に委譲）。

---

## 5. 将来拡張の接続点（現時点では未採用）

以下は **現 MVP スタブが読まない／出力に載せない**が、同じ `dataset_payload` または隣接層に**後から差し込める余地**があるもの。

| 項目 | 想定される挿入場所（概要） |
|------|---------------------------|
| `taxonomy_code` | 入力: `normalization_input_hints` 拡張、または別フィールドで 003 に渡す。出力: 経路メタや `trace_map` の参照。 |
| `decision` / `review_required` | 入力: ゲーティング用フラグ（003 内または materialize 前段）。現状は 004 側 MVP が dataset を**観測**するのみ。 |
| **単位スコープ**（`UNIT_SCOPE_*`） | 入力: hints または 001/002 構造化フィールド。出力: `rows` 付帯メタや別配列（SPEC-TI-003 非スコープの詳細は SPEC 正本）。 |
| **merge 解釈結果** | 入力: 001 `merges` の解決結果または中間表現。転記・スロット生成の前段。 |
| **論理ヘッダグループ** / HeadingTree | 入力: SPEC-TI-010 系。縦持ち・キー解決の主経路（理想 003）。 |
| evidence の追加ルール | `extract_normalization_input_hints_from_judgment_evidence` の拡張で `normalization_input_hints` に載せ、スタブを差し替え。 |

---

## 6. 一文の正本（1〜3 文）

- **003 の現行公式入力（MVP）**は、**`dataset_payload.normalization_input_hints`** を主とし、**001 の `cells`（`raw_display`）** と、必要時のみ **`TableScope` の行範囲**である。  
- **003（MVP）は**、上記を材料に **`rows[]`（転記）・`trace_map`（説明）・`column_slots[]`（列カタログ）** を生成する**変換スタブ層**である。  
- **003（MVP）は**、**taxonomy・decision・列/行の意味の最終確定、evidence の再解釈、merge/ヘッダの確定**はまだ行わない。
