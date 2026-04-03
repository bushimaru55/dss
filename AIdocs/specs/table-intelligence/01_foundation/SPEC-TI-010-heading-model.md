---
id: SPEC-TI-010
title: 見出しモデル仕様書
status: Draft
version: 0.1
owners: []
last_updated: 2026-04-02
depends_on: [SPEC-TI-009]
---

## 1. 目的とスコープ

### 目的

表の **意味構造** を、セル値の羅列ではなく **見出しの階層・軸・セル対応** として表現する **HeadingTree（仮称）** のデータモデルと、構築・欠落時の **継承規則** を定義する。

### スコープ（やる）

- 行見出し・列見出し・多段見出し（階層深さ可変）
- 結合セルに起因する **親子関係** と **セル対応**（どのデータセルがどの見出しに紐づくか）
- 欠落見出し・疑似見出し（書式のみ等）の **フォールバック** 方針（概念レベル）
- SPEC-TI-002 との境界（「見出しセル」かどうかの **確定** は 002、**木構造の形** は本書）

### スコープ外（やらない）

- 生セル格子・ファイル形式（001）
- 信頼度スコア（011）
- 正規化後の列スキーマ（003）— ただし grain の説明のための参照は可

---

## 2. 関係仕様

| 仕様 | 関係 |
|------|------|
| SPEC-TI-009 | 表タイプにより **期待する見出しパターン**（例: クロス表は行列軸必須）が変わる。 |
| SPEC-TI-001 | TableReadArtifact の結合矩形・セルアドレスが入力。 |
| SPEC-TI-002 | 見出しセル候補の **採否**、意味ラベル付与。 |
| SPEC-TI-003 | HeadingTree から **縦持ち** 行を生成する際の写像規則を参照。 |
| SPEC-TI-004 | `dimensions` と HeadingTree の **対応表** を 004 で宣言。 |
| SPEC-TI-006 | `HeadingTree` JSON の正本。 |

---

## 3. 用語定義

| 用語 | 説明 |
|------|------|
| 見出しノード | 1セルまたは結合矩形に対応する論理ノード。`level`（階層深さ）、`axis`（row|column）、`caption`（正規化テキスト）を持つ。 |
| HeadingTree | 見出しノードの **森林**（行側・列側で別木が一般的）。子は「内側の見出し」方向。 |
| 継承 | 内側のデータセルが、外側見出しのラベルを **暗黙に共有** する関係。 |
| セル対応 | データ領域の各セル（または論理行）から、行見出し葉・列見出し葉への **パス** の組。 |
| 疑似見出し | 書式・位置は見出しだがテキストが空・数値のみ等。002 での扱いとセット。 |

---

## 4. 入力・前提

- 対象は **1 TableCandidate** の矩形領域。
- 001 から **結合情報**、**セル値・型**、**書式メタ**（あれば）が渡る。
- 009 の `taxonomy_code` により、**必須軸**（例: CROSSTAB は行軸・列軸の両方）を解釈する。

---

## 5. 出力・成果物

### HeadingTree（概念スキーマ・Draft）

```json
{
  "table_id": "uuid",
  "taxonomy_code": "TI_TABLE_CROSSTAB",
  "row_roots": [{ "node_id": "r0", "children": [] }],
  "column_roots": [{ "node_id": "c0", "children": [] }],
  "nodes": {
    "r0": {
      "axis": "row",
      "level": 0,
      "source_range": "A2:A3",
      "caption": "Region",
      "is_guess": false
    }
  },
  "cell_bindings": [
    {
      "data_cell": "C5",
      "row_path": ["r0", "r1"],
      "column_path": ["c0", "c2"]
    }
  ]
}
```

- **必須（概念）**: `table_id`, `taxonomy_code`, `nodes`, `cell_bindings`（データ領域が空でない場合）
- **任意**: `row_roots` / `column_roots` は実装が隣接リストでも可（006 で物理表現を固定）

### 成果物

- 上記 JSON の **JSON Schema 断片**（006／Phase4 でパッケージ化）
- **継承規則** の疑似コード（§6）
- **失敗パターン集**（§8）

---

## 6. 処理・継承ルール（疑似コード）

```
# 目的: 各 data_cell に (row_path, column_path) を割り当てる

for each data_cell in data_region:
    row_path = nearest row-heading ancestors along row scan order
    column_path = nearest column-heading ancestors along column scan order
    if missing row_path or column_path:
        mark binding as INCOMPLETE  # 002/011 へ
    emit cell_binding(data_cell, row_path, column_path)
```

- **行スキャン順序**: 左→右、上→下。列見出しは上→下、左→右（実装詳細は 001 の座標系に従う）。
- **結合セル**: 結合の **アンカー** セルをノード代表とし、隣接セルとの親子は **002 のルール** に従う（本書は「1ノード1矩形」を前提）。
- **多段見出し**: 外側 level が小さい。内側に進むほど level 増加。

---

## 7. 完全例（3段見出し・概念）

**列見出し3段**（年 → 四半期 → 指標名）、**行見出し2段**（事業部 → 部門）、交差部が数値。

- ノード例: `c_year_2024` (level 0), `c_q1` (level 1), `c_revenue` (level 2)
- データセル `E10` の `column_path`: `[c_year_2024, c_q1, c_revenue]`
- 行側: `[r_div_a, r_dept_sales]`

この例は **008 のゴールデン** に転記する。

---

## 8. 例外・エラー・フォールバック

| 状況 | 挙動 |
|------|------|
| 斜め見出し・非格子 | **未対応**（FORM_REPORT へ寄せ、001 でブロック分割） |
| 見出し欠落 | `is_guess=true` とし 011 でスコア減点 |
| 行見出しのみ／列見出しのみ | 009 のタイプに応じ **必須軸欠落** として 002 が UNKNOWN 扱い可能 |
| デカルト積爆発 | 003 と連携し **スパース binding** または **チャンク分割**（別 SPEC 記述） |

---

## 9. テスト観点

- 3段列見出し×2段行見出しの **binding 件数** と **パス一意性**
- 結合セルが T 字・L 字のときの親子矛盾検出
- 空見出しセルが連続する場合の継承

---

## 10. 未確定事項（暫定案）

| 論点 | 暫定案 |
|------|--------|
| グラフ表現 vs 厳密木 | **DAG 禁止**、森林＋明確な level。実装は隣接リスト推奨。 |
| 見出しセル判定の境界 | **002 正**、010 は「与えられた候補ノードの構造化」のみ。 |
| JSON 物理名 | 006 で camelCase 統一か snake_case かを確定。 |

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-02 | Draft 初版。概念スキーマと継承方針。 |
