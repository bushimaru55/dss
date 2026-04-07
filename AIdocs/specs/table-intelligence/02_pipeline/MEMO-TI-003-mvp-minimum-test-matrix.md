---
id: MEMO-TI-003-MVP-TEST-MATRIX
title: 003 MVP 最小テストマトリクス（現行実装・契約固定）
status: memo
version: 0.1.0
last_updated: 2026-04-07
depends_on:
  - SPEC-TI-003
  - MEMO-TI-003-mvp-official-input-contract.md
  - MEMO-TI-003-mvp-minimum-output-contract.md
---

本メモは [入力契約](MEMO-TI-003-mvp-official-input-contract.md)・[出力契約](MEMO-TI-003-mvp-minimum-output-contract.md) を**壊さない**ための**回帰確認観点**を、ケースと既存テストの対応付けで固定する。**テストコードの追加・変更は行わない**（整理のみ）。

---

## 1. 参照した実装 / テスト

| 種別 | パス |
|------|------|
| 実装 | `backend/table_intelligence/normalization_hints.py`（`build_mvp_rows_and_trace_map_from_hints`, `_build_mvp_column_slots`） |
| 単体（主） | `backend/table_intelligence/tests/test_normalization_hints.py` |
| 結合スモーク | `backend/table_intelligence/tests/test_mvp_pipeline_e2e.py`（`POST job` → `dataset_payload` 全体） |

---

## 2. テスト観点軸（MVP 契約の因子）

| 軸 | 状態 | 契約上の意味 |
|----|------|----------------|
| **行ヒント** | あり / なし | `by_row_index` が空でない vs 空（`table` フォールバックは別軸） |
| **列ヒント** | あり / なし | `by_column_index` が空でない vs 空 |
| **cells** | あり / なし | 転記の有無・`transcribed_cell_trace_count` |
| **スキップ行** | あり / なし | `header_band_skipped` / `note_candidate` / `skipped_row_candidate` が trace に出るか |
| **転記** | あり / なし | `cell_value_transcribed` と `values` の非空 |
| **ヒントのみ列** | あり / なし | 転記のない列 index が `by_column_index` のみでスロットに残るか |
| **ROW_UNKNOWN** | 含む / 含まない | 明示ラベルが付かない行のデータ行化（`rows[]` に入り `values` は空もあり） |

**補助軸（契約メモで重要）**

| 軸 | 説明 |
|----|------|
| **TableScope フォールバック** | `by_row_index` が空のとき `row_min`/`row_max` で走査（**単体では未カバー**） |
| **集計行スキップ** | `ROW_SUBTOTAL` / `ROW_GRAND_TOTAL` → `skipped_row_candidate`（**単体では未カバー**、E2E で kind 集合に含まれることを確認） |

---

## 3. 最小ケースセット（過不足の少ない集合）

**「003 MVP の契約を守れている」と言うための最小集合**（単体中心）の目安は **次の 6〜8 パターン**である。

| # | ケース要約 | カバーする軸 |
|---|------------|----------------|
| 1 | **ヒントなし・table なし** → 空出力 | 行ヒントなし・列ヒントなし・（cells なし） |
| 2 | **行+列ヒント・ヘッダスキップ・cells なし** | スキップあり・列 trace 系・行ヒントあり・列ヒントあり |
| 3 | **ヘッダスキップ + データ行転記** | 転記あり・cells あり・スキップあり |
| 4 | **データ行のみ・cells なし** | 転記なし・rows は 1 件・`values` 空 |
| 5 | **注記行スキップ**（データ行+スキップ） | `note_candidate`・行ヒントのみ（列ヒントなし） |
| 6 | **和集合: ヒント列 + 転記列** | ヒントのみ列あり・転記あり |
| 7 | **全行スキップ + 列ヒントのみ**（`rows` 空・slot のみ） | ヒントのみ列・転記なし・スキップのみ |
| 8（任意） | **trace_ref / trace_kind と slot の整合** | `semantic_lock_in`・列メタの参照整合 |

**統合スモーク（任意だが推奨）**: `test_mvp_pipeline_e2e` で **materialize 経路**の `dataset_payload`（`kind` 部分集合・`column_slots`・stub メタ）を 1 本確認する。

※ **TableScope フォールバック**（`by_row_index` 空 + `row_min`/`row_max`）と **集計行 `skipped_row_candidate` の単体**は、現行 `test_normalization_hints.py` では**明示ケースが不足**（§5 参照）。

---

## 4. ケースごとの期待出力（最低限）

以下は **実装仕様**に沿った期待の骨子。具体件数はフィクスチャに依存する。

### 共通（全ケースで満たすもの）

- **`semantic_lock_in`**: `rows` / `trace_map` / `column_slots` で **`false`**（MVP）。
- **`values_key` / `table_column_index`**: 各 `cN` について **`values_key == "c" + str(N)`** かつ **`table_column_index == N`**。

### ケース別

| ケース | `rows[]` 件数 | `trace_map` の event 系統 | `column_slots` 集合 | 備考 |
|--------|----------------|---------------------------|----------------------|------|
| **ヒント空・table なし** | 0 | なし | 空 | `row_indices` が空 |
| **行+列+ヘッダスキップ（cells なし）** | 1（データ行のみ） | `header_band_skipped` + 列 hint 系（`attribute/measure/column_role_hint`） | `by_column_index` の index 全て | データ行は `values` 空でもよい |
| **ヘッダスキップ + 転記** | 1 | 上記 + `cell_value_transcribed`（セル数分） | 転記列 ∪（列ヒントがあればその列） | ヘッダ行には転記 trace なし |
| **データ行・cells なし** | 1 | 列ヒントのみ（列ヒントがある場合）／なし | 列ヒントに依存 | `values == {}` |
| **注記スキップ** | 1（例: 行0=データ、行2=注記候補） | `note_candidate` + データ行の trace（列ヒントなしなら `slots` 空） | 転記があれば列に依存 | `test_build_mvp_note_candidate_trace`: `by_row_index` が `0` と `2` のみ |
| **和集合（ヒント列+転記列）** | 1 | `cell_value_transcribed` + 列 hint | `by_column_index` ∪ 転記 `cN` | ヒントのみ列は `hint_from_002`、転記なしの列は trace プレビューに転記が無い場合あり |
| **全行スキップ + 列ヒントのみ** | 0 | スキップ系 + 列 hint のみ | `by_column_index` のみ | 転記なし |
| **列のみ変化（転記列集合）** | 1 | `cell_value_transcribed` のみ（列ヒントなし） | 転記された `cN` のみ | セル数で列集合が変わる |

※ `test_build_mvp_note_candidate_trace` は行 `0`=DETAIL、行 `2`=NOTE_CANDIDATE のため **データ行は 1 件**（行 `2` は `note_candidate` でスキップ）。

---

## 5. 既存テストとの対応

### `test_normalization_hints.py`

| テスト関数 | 観点軸（§2） | 主な契約アサーション |
|------------|----------------|------------------------|
| `test_extract_*` / `test_merge_*` / `test_read_hints_from_payload` | 抽出・payload（003 スタブ本体**外**） | evidence → hints、payload マージ |
| `test_build_mvp_empty_row_col_hints_minimal_output` | 行ヒントなし・列ヒントなし・table なし | 空 `rows`/`trace`/`slots` |
| `test_build_mvp_skips_header_puts_col_hints` | 行+列・スキップ・cells なし | `rows` 1、`header`+列 kind、`slots` 2 |
| `test_build_mvp_note_candidate_trace` | スキップ（注記）・列ヒントなし | `note_candidate`、`slots` 空 |
| `test_build_mvp_transcribes_cells_for_data_rows_only` | 転記・cells・スキップ | `values`・`cell_value_transcribed`・`slots` |
| `test_build_mvp_no_cells_leaves_values_empty` | cells なし・データ行 | `values {}` |
| `test_column_slots_union_hints_and_transcribed_only` | 和集合・ヒントのみ列 | index `{0,2}` 等 |
| `test_mvp_column_slots_by_column_index_only_no_transcription` | 全スキップ・列ヒントのみ | `rows` 0、`slots` のみ |
| `test_mvp_column_slots_transcription_only_column_set_follows_cells` | 列ヒントなし・転記のみ | 列数がセルに依存 |
| `test_mvp_column_slots_union_explicit_by_col_and_transcription` | 和集合の明示 | `hint_from_002` の有無 |
| `test_mvp_column_slots_trace_ref_ids_are_trace_map_subset` | trace と slot の整合 | `refs` ⊆ `trace` |
| `test_mvp_column_slots_row_skip_hint_column_without_transcription` | 部分転記・列ヒント | 列1に転記なしでも slot 残る |
| `_assert_mvp_column_slots_contract` | 全該当テスト | `semantic_lock_in` 等 |

### `test_mvp_pipeline_e2e.py`

| 内容 | 補完する観点 |
|------|----------------|
| `test_post_job_materializes_chain_and_gets_resolve` | **materialize 経路**・`dataset_payload` 全体・`kind` の部分集合・**`column_slots` stub**・004 観測 |

### 不足（単体で明示されていない境界）

| 観点 | 状況 |
|------|------|
| **`row_min`/`row_max` フォールバック** | `test_normalization_hints.py` に **なし** |
| **`skipped_row_candidate`（集計行）** | 単体 **なし**（E2E は `kind` に `skipped_row_candidate` を**許容**として含む） |
| **`ROW_UNKNOWN` 明示**（`values` 空のデータ行） | **なし**（実装ではデフォルトでデータ行化しうる） |
| **`ROW_NOTE`（非 CANDIDATE）** | `ROW_NOTE_CANDIDATE` のみ明示（実装は同一扱い） |

---

## 6. 将来追加候補（MVP 外だが回帰で効く境界）

- **merges あり** / 結合セル境界の `cells` キー（`R{r}C{c}` vs `r`,`c` 混在）
- **多段見出し**・論理ヘッダグループ（010 系入力が入った後の 003）
- **合計列 / 備考列 / 単位列**（J2-COL ラベル多様時の `column_role_hint` 分岐）
- **taxonomy 境界**（`TI_TABLE_*` 別の経路選択が入った後の 003）
- **極端に sparse な cells**（列・行が欠けるときの `slots` と `values` の差）
- **TableScope フォールバック**の単体（`by_row_index` 空 + `row_min`/`row_max`）
- **`skipped_row_candidate` の単体**（`ROW_SUBTOTAL` / `ROW_GRAND_TOTAL`）
- **`ROW_UNKNOWN` + 空 `values`** の明示ケース

---

## 7. 一文の正本（回帰で最低限見る場所）

**003 MVP の回帰確認では、`build_mvp_rows_and_trace_map_from_hints` について「空ヒント・スキップ+列ヒント・転記・和集合スロット・trace/slot 整合」が `test_normalization_hints.py` で押さえられており、パイプライン全体は `test_mvp_pipeline_e2e` が `dataset_payload` の `kind`・`rows`・`column_slots`・stub メタを**スモークする**のが最低限である。**  
**単体の空白は、`TableScope` 行レンジフォールバック・集計行スキップ・`ROW_UNKNOWN` 明示**あたりが先に足りない（将来の境界テスト候補）。
