---
id: MEMO-TI-003-MVP-OUTPUT
title: 003 MVP 最小出力契約メモ（現行実装固定）
status: memo
version: 0.1.0
last_updated: 2026-04-07
depends_on: [SPEC-TI-003, MEMO-TI-003-MVP-INPUT]
related: [MEMO-TI-003-mvp-official-input-contract.md]
---

本メモは **現行 backend MVP スタブ**（`build_mvp_rows_and_trace_map_from_hints` が生成する `rows[]` / `trace_map[]` / `column_slots[]`）について、**最低限保証する範囲**と**未保証の範囲**を固定する。[入力契約メモ](MEMO-TI-003-mvp-official-input-contract.md)と対になる。**本書は SPEC の正本を置き換えない**。

---

## 1. 参照した実装 / 仕様

| 種別 | パス / 文書 |
|------|-------------|
| 実装 | `backend/table_intelligence/normalization_hints.py`（`build_mvp_rows_and_trace_map_from_hints`, `_sparse_cells_by_column_in_row`, `_build_mvp_column_slots`, `_table_column_indices_from_values_keys`） |
| 集約 | `backend/table_intelligence/services.py`（`_apply_judgment_hints_to_normalized_dataset` が `dataset_payload` に書き込み） |
| 仕様（MVP 記述） | [SPEC-TI-003](SPEC-TI-003-normalization.md) の「MVP 実装接続」「`rows[].values` の列キーと `column_slots[]`（MVP）」 |
| 入力契約 | [MEMO-TI-003-mvp-official-input-contract.md](MEMO-TI-003-mvp-official-input-contract.md) |
| テスト参照 | `backend/table_intelligence/tests/test_normalization_hints.py` |

---

## 2. `rows[]` の最小契約

### 必ず入るもの（データ行要素ごと）

- **`table_row_index`**: 元表の 0-based 行 index（`by_row_index` のキー、または `row_min..row_max` 走査の `r`）。
- **`values`**: dict。キーは **当面 `c{N}` のみ**（`N` は 0-based 列 index）。`cells` がある行では、稀疏マッチした列について **`raw_display` を文字列化**した値（`None` → 空文字）。セルが無い列はキー自体が存在しない。
- **`logical_row_index`**: `rows[]` 内での 0 始まり連番（スキップ行を除いた**データ行**の並び）。
- **`mvp_stub`: `true`**（MVP スタブ由来の印）。
- **`normalization_hint`**: 少なくとも `from_002_row_kind`（当該行の J2-ROW ラベルまたは `ROW_UNKNOWN`）と **`semantic_lock_in`: `false`**。

### 入ってもよいが「本質」（正規化確定）ではないもの

- **`normalization_hint`** 全体は **002 ヒントの写し**であり、行種の**最終確定**ではない。

### 入れてはいけないもの（MVP スタブの責務外として置かない）

- **スキップ対象行**（下記）を **`rows[]` の要素として**含めない。
- **`raw_display` 以外から捏造したセル値**、型確定後の数値・日付オブジェクト、taxonomy に基づく**意味付け済みの論理列 ID** への置換（現実装は行わない）。
- **`dimensions` / `measures` 確定**や **`semantic_lock_in`: `true`** による意味ロックイン（MVP は `false` 固定）。

### 行スキップ時の扱い（`rows[]` に出ない）

次の **`by_row_index` ラベル**の行は **`rows[]` に含めず**、**`trace_map` のみ**（`kind` 下記）。

| 条件 | `trace_map.kind` |
|------|------------------|
| `ROW_HEADER_BAND` | `header_band_skipped` |
| `ROW_NOTE` / `ROW_NOTE_CANDIDATE` | `note_candidate` |
| `ROW_SUBTOTAL` / `ROW_GRAND_TOTAL` | `skipped_row_candidate` |

上記以外（実装上は **`ROW_UNKNOWN` を含む**）は「データ行」として **`rows[]` に 1 行追加**されうる（`cells` が空なら `values` は `{}` のまま）。

### `values` のキーが `cN` であることの位置づけ

- **互換の正（MVP）**: 列は **table 列 index** を `c{0-based}` で表す。**論理列 ID へのリネームはしない**（[SPEC-TI-003](SPEC-TI-003-normalization.md) MVP 節と一致）。
- **未保証**: `c` + 数字以外のキー、列の意味名、004 の measure 名。

### `raw_display` 転記と意味確定の分離

- **転記**: `values["cN"]` は **001 の観測**に限り、**文字列として**載せる。
- **意味確定**: 行種・列役割は **002 ヒントの候補**として `normalization_hint` や `trace_map` に残るにとどまり、**004 の dimensions/measures やビジネス意味の確定ではない**。

---

## 3. `trace_map[]` の最小契約

### 目的

- **説明責任**: どの **table 行・列**について、スタブが**スキップしたか・転記したか・列ヒントを付したか**を追えるようにする。
- **`rows[]` に載らない事実**（スキップ行、列単位のヒント、セル単位の転記）を **ここに残す**。

### 実装上ありうる `kind`（最低限の列挙）

| `kind` | 主な用途 |
|--------|-----------|
| `header_band_skipped` | 見出し帯行のスキップ |
| `note_candidate` | 注記行候補のスキップ |
| `skipped_row_candidate` | 集計行（小計・総計）のデータ本体からの除外 |
| `cell_value_transcribed` | データ行の **1 セル**あたりの転記（`table_row_index`, `table_column_index`, `logical_row_index`, `values_key`） |
| `attribute_column_candidate` | J2-COL が属性系のときの列ヒント |
| `measure_column_candidate` | J2-COL が度量系のときの列ヒント |
| `column_role_hint` | 上記以外の J2-COL ラベルに対する列ヒント |

各エントリは原則 **`semantic_lock_in`: `false`** と **`trace_ref`**（スタブ内で一意にしうる文字列）を持つ。

### `rows` / `column_slots` に載せず `trace_map` に残すもの

- **スキップ行**の事実（`rows[]` には出ない）。
- **セル単位**の転記根拠（`rows[].values` は集約結果のみのため、**セル粒度**は `trace_map`）。
- **列ヒント**（J2-COL 由来の `attribute_column_candidate` 等）は **列カタログ**（`column_slots`）と重複しうるが、**trace 上の `kind` / `note` は説明用**。

### review / 監査 / デバッグとの関係

- **人確認（005）や正式監査ログの正本ではない**。MVP は **開発・接続確認・下流の参照観測**に足る粒度。
- **デバッグ**: `trace_ref`・`note` でスタブの判断を辿れることを意図。

### `trace_map` を正本としてはいけないもの

- **002 / 004 の最終判定**、**taxonomy**、**dimensions/measures の確定**。
- **完全なセル網羅**（稀疏で存在しないセルは trace も作られない）。
- **merge 解釈・結合セル範囲**の正本（実装は `cells` の観測キーに依存）。

---

## 4. `column_slots[]` の位置づけ（出力全体の中で）

### `rows[]` / `trace_map[]` との役割差

| 出力 | 役割 |
|------|------|
| `rows[]` | **論理データ行**と **`cN` による値の転記**（表の「中身」）。 |
| `trace_map[]` | **行スキップ・セル転記・列ヒント**の**説明**（イベント列挙）。 |
| `column_slots[]` | **列 index と `cN` の対照表**に近い **列カタログ**（`hint_from_002`・trace から拾った**参照**）。 |

### 保証するもの

- **スロット集合**は **`by_column_index` のキー（列 index）** と **`rows[].values` に現れた `cN`** の**和集合**（実装コメントどおり）。
- 各スロットに **`slot_id`**（例 `col_{N}`）、**`table_column_index`**、**`values_key`**（`c{N}`）、**`semantic_lock_in`: `false`**。
- 任意: **`hint_from_002`**, **`trace_kind_preview`**, **`trace_ref_ids`**（`trace_map` から **同一 `table_column_index`** のエントリを集めた説明用メタ）。

### まだ保証しないもの

- **taxonomy** や **004** への **dimension/measure の割当確定**。
- **結合セル・多段見出し**解決後の論理列。
- **スロット集合**が「表の全列」を列挙すること（**ヒント列 ∪ 転記列**のみ）。

---

## 5. 出力間の対応関係（最低限の整合契約）

以下は **同一 `build_mvp_rows_and_trace_map_from_hints` 呼び出しの結果**として期待する。

1. **`rows[].values` のキー**  
   - 形式は **`c{N}`**（`N` は非負整数）。**`N` は `table_column_index` と一致**する。

2. **`column_slots[]`**  
   - 各要素の **`table_column_index` = `N`** のとき **`values_key` は `"c" + str(N)`**（実装は `f"c{ci}"`）。
   - **`rows` に `cN` が存在する列 index `N`** は **スロット集合に含まれる**（その行がデータ行であること）。

3. **`by_column_index` に alone で現れる列 index**  
   - **`rows` にその列の転記が無くても**、**`column_slots` にスロットが現れる**（和集合の左側）。

4. **`trace_map`（`cell_value_transcribed`）**  
   - 同一セルについて **`table_row_index` / `table_column_index` / `values_key`** は **`rows` の該当行・列と一致**する。  
   - **`logical_row_index`** は **その時点の `rows` における `logical_row_index`** と一致する。

5. **列ヒント系 trace**（`attribute_column_candidate` 等）  
   - **`table_column_index`** は **`column_slots` の同一 index** と指す同じ物理列である。  
   - **意味の確定**は行わない（複数 `kind` が同一列に付きうる）。

6. **未要求**  
   - `trace_map` の**配列順序**を API 契約として固定しない（テストは内容集合・参照整合でよい）。

---

## 6. 最小テスト観点（実装変更なし・将来テスト化向け）

- **データ行のみ** `rows[]` に含まれる（スキップ種別の行は含まれない）。
- **スキップ行**は `trace_map` に **`header_band_skipped` / `note_candidate` / `skipped_row_candidate`** のいずれかで残り、**`rows` には残らない**。
- **転記が発生した列**（`values` に `cN` がある）は **`column_slots`** に **`table_column_index` = `N`** の要素がある。
- **`by_column_index` のみ**で転記のない列でも、その **index は `column_slots` に現れる**。
- **`cell_value_transcribed`** の `table_row_index` / `table_column_index` / `values_key` / `logical_row_index` が **対応する `rows[]` 要素と矛盾しない**。
- **`values` の各キー**が `c` + 数字形式であり、**列 index と対応**する。
- **`ROW_UNKNOWN` のデータ行**は `rows[]` に入りうる（空 `values` でも）。
- **`semantic_lock_in`** が **`rows` / `trace_map` / `column_slots` で false** であること（MVP）。

---

## 7. 一文の正本（1〜3 文）

- **`rows[]`** は、**スキップされなかった table 行について、`cN` キーに 001 の `raw_display` を載せた論理行の列挙**であり、**意味・型の確定**ではない。  
- **`trace_map[]`** は、**スキップ・セル転記・列ヒント**を **説明するためのイベント列**であり、**監査正本・最終判定**ではない。  
- **`column_slots[]`** は、**列 index と `cN` の対照**および **002 列ヒント／trace からの参照付きカタログ**であり、**taxonomy や 004 の割当確定**ではない。  
- **まだ確定しないもの**は、**taxonomy、decision、evidence の再解釈、merge 解決、列・行のビジネス意味、dimensions/measures** である。
