---
id: SPEC-TI-005
title: 人確認フロー仕様書
status: Draft
version: 0.2
owners: []
last_updated: 2026-04-08
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-003, SPEC-TI-004, SPEC-TI-006, SPEC-TI-009, SPEC-TI-010]
---

## 文書目的

[SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md)〜[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md) のパイプラインで**残った曖昧性・不足・競合・部分失敗**を、**人が確認し解消する**ための**確認フローと状態遷移の正本**を定義する。

**明記（責務の正本）**

- **001〜004 は「人確認の入力を作る側」**であり、**本仕様（005）が解消フローの正本**である。  
- **005 は読取・判定・正規化・分析メタ生成を実行しない**（各ステージの正本は 001／002／003／004）。005 は **いつ・何を・どの順で確認し、結果をどこへ戻すか**を定義する。  
- **[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md)** の **`review_required`／`review_points[]`** を**主入力**として受け取り、**確認順序・優先度・解消パス**を定義する（[§review_points の前提](SPEC-TI-004-analysis-metadata.md)）。  
- 確認結果は **002（再判定）／003（再正規化）／004（再メタ生成）** の**再実行または再解釈**へ接続する（§再判定・再正規化・再メタ生成への接続）。  
- **本仕様は UI 文言・画面デザインの正本ではない**。**確認ロジック・状態遷移・質問タイプ・回答形式の契約**が正本（具体文言・ワイヤーは [SPEC-TI-007](../05_experience_quality/SPEC-TI-007-ui.md)）。  
- **[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)** へは、**解消状態の粒度**（§011 へ渡す解消状態の粒度）と**どの論点が解消されたか**を**引き継げる前提**を持つ（数式は 011）。  
- **[SPEC-TI-013](SPEC-TI-013-suggestion-generation.md)** へは、**候補抑制レベル**（§013 へ渡す候補抑制レベル）を渡し、**未解消時の扱い**を 013 と共有する（候補ロジック自体は 013）。

---

## スコープ

- **人確認へ遷移する条件**（`review_required`・`review_points`・上流ステータスとの関係）
- **`review_points` の受け取り方**（004 の `point_id`／`category`／`priority`／`affected_fields`／`trace_refs`／`suggested_resolution_type` を前提）
- **確認対象の優先順位**と**確認ステップの順序**
- **質問タイプ**・**回答形式**
- **再判定／再正規化／再メタ生成**への接続と**差分入力**の扱い
- **低 IT リテラシー利用者**向けの配慮（粒度・用語・負担）
- **解決不能時**（部分解決・保留・エスカレーション・013 抑制）
- **確認結果の保持方針**（`HumanReviewSession` との関係）

---

## 非スコープ

以下は**詳細確定しすぎない**。委譲先を明記する。

- **読取ロジック**（001）・**判定ロジック**（002）・**正規化ロジック**（003）・**分析メタ生成の中身**（004 のアルゴリズム）  
- **信頼度の数式**・閾値（[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)）  
- **分析候補生成ロジック**（[SPEC-TI-013](SPEC-TI-013-suggestion-generation.md)）  
- **UI の具体文言・画面デザイン**（[SPEC-TI-007](../05_experience_quality/SPEC-TI-007-ui.md)）  
- **API／DB 物理設計**（[SPEC-TI-014](../04_system/SPEC-TI-014-api.md)／[SPEC-TI-015](../04_system/SPEC-TI-015-db.md)）

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 人確認セッション | [SPEC-TI-006 §5.9](../01_foundation/SPEC-TI-006-io-data.md) の `HumanReviewSession`。`session_id`・`table_id`・`state`・`pending_questions[]` を持つ。 |
| review point | [SPEC-TI-004](SPEC-TI-004-analysis-metadata.md) が列挙する**論点 1 条**。005 の**キュー要素**の主入力。 |
| 解消 | 利用者の回答により、**不確実性が減る**状態。上流オブジェクトの**再生成**または**メタの更新**を伴いうる。 |
| 再実行 | 002／003／004 のいずれかを**同じ入力ファイル**から**やり直す**ジョブ（014 で詳細化）。 |
| 部分解決 | review points の**一部のみ**解消。残りは保留または次サイクル。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) | 原本。**再読取**が必要なときは 001 パイプラインへ戻す（005 は読取しない）。 |
| [SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) | **再判定**の正本。**JudgmentResult** の更新入力を受け取る。 |
| [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) | **再正規化**の正本。**NormalizedDataset** の再生成。 |
| [SPEC-TI-004](SPEC-TI-004-analysis-metadata.md) | **`review_points` の生成元**。**再メタ**の正本。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | `HumanReviewSession` の必須フィールド。**state 遷移は 005 正本**。 |
| [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) | 表種別の語彙。人が**選択する**場合は 009 の enum のみ（002 と整合）。 |
| [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) | 見出し修正が必要な場合、002／003 経由で間接的に影響。005 は木を編集しない。 |
| SPEC-TI-011 | **解消済み／未解消**の不確実性を受け取る。 |
| SPEC-TI-013 | **未解消 review** 時の**候補抑制**前提。 |

---

## 人確認フローの位置づけ

表解析パイプラインにおいて、005 は次に限定する。

1. **論点のキューイング**: `review_points[]` を **priority／category** で並べ、**1 論点ずつ**または**バッチ**で提示する方針を定める。  
2. **解消パスの選択**: `suggested_resolution_type` と整合する**再実行先**（002／003／004）を決める。  
3. **結果の永続化**: 回答を **HumanReviewSession** および**上流の差分 PATCH**（014）に載せうる構造にする（詳細は 014）。  
4. **下流への伝播**: 011（信頼度）・013（候補）が**同じ解消状態**を参照できるようにする。  

**境界の再掲**: **005＝確認フロー**、**007＝画面表現**、**011＝スコア**、**013＝候補生成**。

---

## 入力

### 主入力（必須）

- **`AnalysisMetadata`**（[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md)、006 §5.8）  
  - **`review_required`**（真なら人確認を起動しうる）  
  - **`review_points[]`** — 各要素は **004 の最小構造**（`point_id`, `category`, `priority`／`severity`, `affected_fields`, `trace_refs`, `suggested_resolution_type`）を**前提にできる**こと。  
- **`table_id`** — 対象表。  
- **参照**: **`JudgmentResult`**（002）、**`NormalizedDataset`**（003）の**ID または埋め込み参照**（同じ `table_id`）。005 は**中身を再計算しない**が、**再実行のトリガ**に使う。

### 補助入力（推奨）

- 003 の **`normalization_meta`**（`PARTIAL`／`FAILED`・`incomplete_bindings` 等）— **論点の説明・優先度**の補強。  
- 001 の **`parse_warnings`** — **再読取**判断の補助。  
- 002 の **`evidence[]`** — **曖昧性**の原文。

---

## 出力

### 主成果物: `HumanReviewSession`（更新）

[SPEC-TI-006 §5.9](../01_foundation/SPEC-TI-006-io-data.md) を満たす。

| フィールド | 005 における意味（暫定） |
|------------|----------------------------|
| `session_id` | セッション一意 ID。 |
| `table_id` | 入力と同一。 |
| `state` | **005 定義の暫定ステート**（§`state` の暫定モデル）。006 正式 enum は Phase4 で同期。 |
| `pending_questions[]` | **未完了の論点**（`point_id` 対応）。§pending_questions と answers の関係。 |

### `state` の暫定モデル（Draft 0.2）

006 の JSON Schema 確定前の**概念モデル**。014 がジョブと同期しやすいよう**意味**を固定する。

| 状態 | 意味 |
|------|------|
| `OPEN` | セッション作成済み。**未着手**または**キュー投入直後**。 |
| `IN_PROGRESS` | **少なくとも 1 論点**について回答収集中。 |
| `WAITING_RERUN` | 回答により **002／003／004 の再実行**がキューに載り、**完了待ち**。 |
| `PARTIALLY_RESOLVED` | **一部の `point_id` のみ**解消。`pending_questions[]` に残あり。 |
| `RESOLVED` | **セッション目的どおり**論点が処理完了（再実行後の 004 取り込みまで含めて完了した状態）。 |
| `CLOSED_UNRESOLVED` | セッション終了だが **未解消論点が残る**（利用者スキップ・打ち切り等）。 |
| `ESCALATED` | **運用／上位権限**へ移管（012／014）。 |

遷移の**厳密なステートマシン図**は Phase4 可。**禁止遷移**（例: `RESOLVED` からの無断戻り）は 014／実装で定める。

### 副次成果物（概念・006 MINOR）

- **`answers[]`**（概念）: `point_id`・回答内容・時刻・回答者ロール。  
- **`review_session_resolution_grade`**（概念）: §011 へ渡す解消状態の粒度（011 の重み付け入力）。  
- **`suggestion_suppression_level`**（概念）: §013 へ渡す候補抑制レベル。  
- **`upstream_rerun_plan`**（概念）: 002／003／004 の**どれを再実行するか**のリスト。  
- **011 向け**: **human_resolved_uncertainty[]** — どの `point_id`／`category` が解消されたか（数式は 011）。  
- **013 向け**: **`review_open_count`**（補助）と **`suggestion_suppression_level`**（主）。

---

## 人確認の原則

1. **正本の尊重**: 001〜004 の**責務を越えて**新しい「事実」を捏造しない。確認は**選択・追記・差分**として表現する。  
2. **review_points 中心**: キューは **`point_id`** で追跡する。  
3. **後続影響が大きい論点を先に**: **表種別・見出し・単位・grain・主要軸**を優先（§確認対象の優先順位）。  
4. **全部解けなくてよい**: **部分解決・保留**を許容し、**011／013** に正直に渡す。  
5. **用語**: 画面では**やさしい言い換え**（007）。005 は**論理名と対応**を定義する。  
6. **トレーサビリティ**: **`trace_refs`** を利用者が**確認できる**前提（原本の見え方は 007）。

---

## 人確認へ遷移する条件

次のいずれかを満たすと**人確認を起動しうる**（製品で強制／任意は別途）。

| 条件 | 主な根拠（上流） |
|------|------------------|
| `review_required === true`（004） | 004 の宣言 |
| `review_points[]` が非空 | 004 |
| 002 `decision === NEEDS_REVIEW` | 002（004 に未反映の場合も起動しうる） |
| 003 `normalization_status` が `PARTIAL`／`FAILED` | 003 メタ（004 の review に反映済みを推奨） |

**明記**: 005 は**これらを再判定しない**。**遷移条件の評価**は実装が 004／ジョブオーケストレーションで行い、**005 は受理した論点を処理する**。

---

## review_points の分類方針

004 の **`category`** を**そのまま**キュー分類に用いる（新語を増やさない）。例（004 準拠・拡張は 004 MINOR）:

| category（例） | 解消の典型パス（暫定） |
|----------------|-------------------------|
| `BINDING_INCOMPLETE` | 見出し／軸の確定 → **002 再判定**または **003 再正規化**（010 前提は 002／003） |
| `UNIT_CONFLICT` | 単位の選択・除外 → **004 再メタ**（または 002 で列役割更新） |
| `GRAIN_HYPOTHESIS` | grain の確定 → **004 再メタ**が主。 |
| `NORMALIZATION_PARTIAL` | 範囲の許容／再実行 → **003 再正規化**または **004 の filters 更新** |

**`suggested_resolution_type`**（004）を**優先ヒント**とし、005 が**最終的な再実行パス**にマッピングする（§接続表）。

### category と標準質問タイプの対応（Draft 0.2 暫定）

**厳密な固定表ではない**が、後述の「質問タイプの定義」と 004 の `category` を**007／014 が突き合わせやすい**よう標準候補を示す。

| `review_points.category`（例） | 標準となりうる質問タイプ |
|----------------------------------|---------------------------|
| `BINDING_INCOMPLETE` | `REGION_ACK`／`SINGLE_CHOICE` |
| `UNIT_CONFLICT` | `SINGLE_CHOICE` |
| `GRAIN_HYPOTHESIS` | `SINGLE_CHOICE`／`CONFIRM_DENY` |
| `NORMALIZATION_PARTIAL` | `REGION_ACK`／`CONFIRM_DENY` |
| **taxonomy 変更系**（表種別の確定・変更） | `SINGLE_CHOICE` |
| **dimension／axis 解釈系** | `SINGLE_CHOICE`／`MULTI_CHOICE` |

---

## 確認対象の優先順位

**高い順（暫定標準）** — 「後続全体に効くものほど先」。

1. **表種別（taxonomy）の確定**（002 の選択・曖昧性解消）  
2. **見出し／軸（binding・行／列の意味）**（002→003 に影響）  
3. **単位・通貨**（measure・集計の解釈）  
4. **grain（1 行の意味）**（004）  
5. **主要 dimension／time 軸**（004）  
6. **部分失敗の原因**（003 `PARTIAL`・欠落領域の許容／再実行）  
7. **注記・集計行の扱い**（主分析に含めるかの確認）

**同順位**は **`priority`／`severity`**（004）→ **`point_id` の安定ソート**（暫定）。

---

## 確認ステップの順序

1. **セッション開始**: `state = OPEN`。`pending_questions[]` に `review_points` を**優先順位で**格納。  
2. **論点ごとの提示**: `state = IN_PROGRESS`。`trace_refs` に基づき**対象セル・範囲**を示す（UI は 007）。  
3. **回答収集**: §質問タイプ・§回答形式。§pending_questions と answers の関係に従い `pending_questions[]` を更新。  
4. **中間コミット**: 再実行が要る場合 `state = WAITING_RERUN`。不要なら **即時**に次論点へ。  
5. **再実行完了待ち**（002／003／004）— 014 のジョブモデルに委譲。  
6. **再メタ取り込み**: 004 の `AnalysisMetadata` を更新し、**残りの review_points** で `pending_questions[]` を**再構築**しうる。  
7. **終了**: `RESOLVED`／`PARTIALLY_RESOLVED`／`CLOSED_UNRESOLVED`／`ESCALATED`（§解決不能時）。

---

## 質問タイプの定義

厳密な UI 文は書かない。**論理タイプ**のみ。

| タイプ ID（概念） | 説明 | 例（意図） |
|-------------------|------|------------|
| `SINGLE_CHOICE` | **単一選択**（taxonomy・単位・grain 候補） | 「この表は次のどれに近いですか」 |
| `MULTI_CHOICE` | **複数選択**（有効な dimension・期間） | 「どの列を比較に使いますか」 |
| `CONFIRM_DENY` | **はい／いいえ** | 「この行は集計行として除外してよいですか」 |
| `FREE_TEXT` | **短い自由記述**（補足のみ） | 主判断は選択肢に寄せる |
| `REGION_ACK` | **範囲の確認**（skipped／binding 欠落） | 「この部分は分析対象外でよいですか」 |

---

## 回答形式の定義

| 形式 | 内容 | 下游への載せ方（概念） |
|------|------|-------------------------|
| **選択肢 ID** | 009 の `taxonomy_code` 等、**列挙値**にマップ | 002 PATCH 入力 |
| **論理列 ID／dimension ID** | 004 の `affected_fields` と整合 | 004 PATCH |
| **許容／拒否** | 範囲・集計行の除外 | 003 `filters` 相当、004 更新 |
| **スキップ** | 「今は決めない」 | `point_id` を **保留** |

---

## pending_questions と answers の関係（Draft 0.2）

回答後に `pending_questions[]` がどう変わるかの**基本パターン**（実装詳細は 014／015）。

| パターン | `pending_questions[]` の扱い | `state` の例 |
|----------|------------------------------|--------------|
| **回答により即時クローズ** | 当該 `point_id` を**キューから除去**。再実行不要なら次論点へ。 | `IN_PROGRESS` → 同／`PARTIALLY_RESOLVED` |
| **回答後に rerun が必要** | 論点は**一時的に保留**または「実行中」マーク。**再実行完了まで**新規回答をブロックしうる。 | `WAITING_RERUN` |
| **依存論点が残る** | 当該 `point_id` は除去するが、**別 `point_id` が同じ原因に依存**→ **pending 継続**。 | `IN_PROGRESS`／`PARTIALLY_RESOLVED` |
| **スキップ／わからない** | **除去しない**または **UNRESOLVED フラグ**付きで残す。**解消粒度・候補抑制レベル**（後述）に反映。 | `PARTIALLY_RESOLVED`／`CLOSED_UNRESOLVED` |

**`answers[]`**（概念）には**常に** `point_id` と**生の回答**を残し、`pending_questions[]` の差分と**突合可能**にする（監査）。

---

## 再判定・再正規化・再メタ生成への接続

### どの確認結果がどこへ戻るか（暫定標準）

| 変化の内容 | 再実行の正本 | 備考 |
|------------|--------------|------|
| **表種別・見出し採否・行種別・列役割**の変更 | **002** | `JudgmentResult` 更新。必要なら **003→004** を続けて実行。 |
| **縦持ち経路・結合補完・単位の物理付与**の変更 | **003** | `NormalizedDataset` 再生成。**004 は必ず後続**。 |
| **grain・dimensions／measures・filters・aggregations の意味だけ**の変更 | **004** | 003 の出力は**同一でもよい**（解釈のみ変更）。 |
| **読取の誤り**（セル値・範囲） | **001**（再読取）→ **002→003→004** | 005 は読取しない。**再アップロード／再 OCR** 等は 014。 |

### `suggested_resolution_type` との対応（例）

| suggested_resolution_type（004） | 典型パス |
|-----------------------------------|-----------|
| `HUMAN_CHOICE_AXIS` | 回答を 002 または 004 PATCH に反映 → **必要なら** §標準 rerun chain |
| `RE_READ` | **001 起点**のジョブチェーン（§例） |
| `ACCEPT_PARTIAL` | **004 のみ**（`filters`／`review` 状態）。003 再実行なしでもよい |

### 標準 rerun chain と例（Draft 0.2）

014 のジョブ DAG は 014 正本。**005 が期待する「戻し先の標準」**のみ以下に示す。

| トリガ（人確認の結果） | **標準 rerun chain** | **必要に応じて続ける chain** |
|------------------------|----------------------|--------------------------------|
| **表種別（taxonomy）変更** | **002 → 003 → 004** | なし（上記で一巡） |
| **見出し採否・軸（binding 前提）変更** | **002 → 003 → 004** | 同上 |
| **grain・dimensions／measures の意味だけ再解釈** | **004 のみ** | — |
| **単位の「意味」だけ修正**（メタ上の解釈） | **004 のみ** | — |
| **単位の物理付与・列への再マッピング** | **003 → 004** | — |
| **読取範囲・セル観測の誤り** | **001 → 002 → 003 → 004** | 001 内の再試行は 001／014 |

**再メタのみで済むケース**: 上表「**004 のみ**」。**NormalizedDataset** は同一 ID のまま**再利用**しうる（実装は 014）。

**再読取からやり直すケース**: **001 起点**。その後は必ず **002→003→004** を順に実行する**完全チェーン**を標準とする。

---

## 011 へ渡す解消状態の粒度（Draft 0.2）

数式・閾値は **011 正本**。005 はセッション単位で次の**概念粒度**を渡し、011 が**重み付け**しやすくする。

| `review_session_resolution_grade`（概念） | 意味 |
|-------------------------------------------|------|
| `FULLY_RESOLVED` | **意図した論点がすべて**処理され、**未解消 `point_id` なし**（または製品定義の「必須のみ」完了）。 |
| `PARTIALLY_RESOLVED` | **一部**の `point_id` が解消。**残 pending** あり。 |
| `UNRESOLVED` | **必須論点が未解消**のまま終了、または**回答なし**。 |
| `SKIPPED_BY_USER` | 利用者が**明示的にスキップ**（「わからない」「後で」）。**UNRESOLVED と区別**しうる（011 で別減点）。 |

**human_resolved_uncertainty[]** と併用し、**どの category が人により解消されたか**を列挙する（011 入力）。

---

## 013 へ渡す候補抑制レベル（Draft 0.2）

候補の**中身・並び**は **013 正本**。005 は **`suggestion_suppression_level`**（概念）で**前提レベル**だけを渡す。

| レベル | 意味（前提） |
|--------|----------------|
| `SUGGESTION_BLOCKED` | **未解消 review** または **信頼不能**に近く、**候補生成を行わない**製品方針。 |
| `SUGGESTION_LIMITED` | **少数・低リスク**の候補のみ、または **明示ラベル付き**のみ出す前提。 |
| `SUGGESTION_ALLOWED_WITH_CAUTION` | 候補は出すが **注意喚起**・**011 低スコア**とセット（013／007）。 |

**`review_open_count`** と **011 のスコア**と組み合わせて 013 が最終判断してよい（005 は**レベル宣言**まで）。

---

## 解決不能時の扱い

| 状況 | 暫定方針 |
|------|-----------|
| **利用者が判断を拒否** | `point_id` を **UNRESOLVED** として残す。`state = CLOSED_UNRESOLVED` または `PARTIALLY_RESOLVED`。 |
| **時間切れ・エスカレーション** | `state = ESCALATED`。**運用アカウント**または**後処理**へ移す（012／014）。 |
| **011** | **`review_session_resolution_grade`**（`UNRESOLVED`／`SKIPPED_BY_USER` 等）と **human_resolved_uncertainty[]** を渡す。 |
| **013** | **`suggestion_suppression_level`** を **`SUGGESTION_BLOCKED` または `LIMITED`** にしうる（013 正本で最終決定）。 |

**全部解けなくてよい**: **部分解決**は正式な終了状態とする。

---

## 低 IT リテラシー利用者向け配慮

- **1 画面 1 決定**を**推奨**（負担分散）。  
- **専門用語の回避**: 内部名は **「表の種類」「列の役割」「時間の列」** 等に**言い換え**（対応表は 007）。  
- **選択肢中心**: 自由記述は**補足**に限定。  
- **原本の見せ方**: `trace_refs` を**ハイライト**等で示す（実装は 007）。  
- **失敗の許容**: 「わからない」「このままでよい」は**正当な回答**として定義しうる。

---

## 確認結果の保持方針

- **`HumanReviewSession`**: **state** と **`pending_questions[]`** の更新履歴を残しうる（監査）。  
- **回答**: `point_id` 単位で**追跡可能**にする（006 MINOR で `answers[]` 正式化）。  
- **上流オブジェクト**: 002／003／004 の**新バージョン ID**（`judgment_id`／`dataset_id`／`metadata_id`）を**セッションに紐づけ**る（014）。  
- **改ざん防止**: 原本ファイルハッシュ（001）との**突合**はジョブ設計で（014／015）。

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| 画面文言・コンポーネント | SPEC-TI-007 |
| REST／ジョブ・PATCH 形式 | SPEC-TI-014 |
| 永続化スキーマ | SPEC-TI-015 |
| 信頼度の式 | SPEC-TI-011 |
| 候補の並び・テンプレ | SPEC-TI-013 |
| `HumanReviewSession` JSON Schema 完全形 | SPEC-TI-006 Phase4 |

---

## レビュー観点

- **`review_points` が欠落せず**キューに入るか。  
- **category → 質問タイプ**の対応が**一貫**しているか（007／014）。  
- **優先順位**が後続パイプラインと**矛盾しない**か。  
- **標準 rerun chain** が**誤接続**していないか。  
- **`state` 暫定モデル**と **`pending_questions[]` 更新**が運用と整合するか。  
- **`review_session_resolution_grade`**／**`suggestion_suppression_level`** が 011／013 に**正直に**伝わるか。  
- **低 IT** 向け配慮が**フロー上**で実現可能か（007 と齟齬ないか）。

---

## 初版成立ライン

- **遷移条件**・**review_points 受け取り**・**優先順位**・**ステップ順**が文章化されている。  
- **質問タイプ**・**回答形式**が定義されている。  
- **002／003／004 への接続表**がある。  
- **解決不能・部分解決**・**013 抑制前提**が述べられている。  
- **001／002／003／004／011／013** との境界が明確。

**Draft 0.2 追加確認**: **category×質問タイプ**、**標準 rerun chain**、**`state` 暫定値**、**pending／answers パターン**、**011 解消粒度**、**013 抑制レベル**が参照できること。

---

## 補足メモ（初版の外枠）

### この初版で未確定の論点（Draft 0.2 時点）

- 上記 **`state` 列挙**の **006 JSON Schema への正式取り込み**と**禁止遷移**の完全列挙。  
- **1 セッション複数 table** の可否。  
- **回答の必須度**（必須論点 vs 任意）と **`SKIPPED_BY_USER` の製品定義**。  
- **`suggestion_suppression_level`** を **011 スコアと自動連動**するか（手動フラグか）。  
- **エスカレーション**の運用 SLO（012 連携）。

### SPEC-TI-011 に引き継ぐ事項

- **`review_session_resolution_grade`**（`FULLY_RESOLVED`／`PARTIALLY_RESOLVED`／`UNRESOLVED`／`SKIPPED_BY_USER`）と **自動スコア**の合成。  
- **human_resolved_uncertainty[]**（`point_id`／`category` 単位）の**減点・加点**。  
- **`SKIPPED_BY_USER` と `UNRESOLVED` の差分**スコア。

### SPEC-TI-013 に引き継ぐ事項

- **`suggestion_suppression_level`** と **`review_open_count`**・**011** の**組合せ規則**。  
- **`SUGGESTION_ALLOWED_WITH_CAUTION`** 時の **UI 表現**（007）。  
- **ジョブ状態**との同期（014）。

### SPEC-TI-001／002／003／004／006 との自己点検結果

| 観点 | 結果 |
|------|------|
| 001 | **整合**。再読取は 001 パイプラインへ委譲。005 は読取しない。 |
| 002 | **整合**。再判定は 002 正本。005 は PATCH を指示するのみ。 |
| 003 | **整合**。再正規化は 003 正本。 |
| 004 | **整合**。`review_points` を主入力とし、再メタは 004。 |
| 006 | **整合**。`HumanReviewSession` 必須フィールドを尊重。拡張は MINOR。 |

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.2 | 2026-04-08 | category×質問タイプ、標準 rerun chain、`state` 暫定モデル、pending／answers パターン、011 解消粒度、013 抑制レベル。 |
| 0.1 | 2026-04-07 | 初版本文。review_points 中心、優先順位、再実行接続、低IT、未解消、011／013 前提。 |
