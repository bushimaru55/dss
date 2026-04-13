---
id: SPEC-TI-005
title: 人確認フロー仕様書
status: Draft
version: 0.2.2
owners: []
last_updated: 2026-04-08
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-003, SPEC-TI-004, SPEC-TI-006, SPEC-TI-009, SPEC-TI-010, SPEC-TI-011, SPEC-TI-013]
---

## 文書目的

[SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) の読取曖昧性、[SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) の判定曖昧性、[SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) の正規化制約（`PARTIAL`／`FAILED` 等）、必要に応じて [SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) の信頼度情報を受け、**どの条件で人確認へ遷移し、何を確認し、回答後に再判定・再正規化へどう戻すか**を定義する**正本**とする。

**明記（責務）**

- **005 は人確認フローの正本**である。**001** は読取、**002** は判定、**003** は正規化、**004** は意味メタ（`review_points` の生成元）、**011** は信頼度、**013** は候補生成の各**正本**であり、005 はこれらを**再実行しない**。  
- **[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md)** の **`review_required`／`review_points[]`** を**主入力**とする（004 が論点を構造化する）。**標準経路**は **`001 → 002 → 003 → 004 → 005`** である。**005 は `review_points` を再生成する正本ではない**。  
- **`suggestion_suppression_level` の正本は本書（005）**である。**011 はこのレベル値を確定しない**（抑制を**強めるべき信号**や**スコア帯に基づく推奨**を出しうる）。**013 は 005 の宣言を必ず尊重**し、**011 の信号を補助材料**として候補の並び・件数・弱化を制御する。**011 も 013 も互いの上流成果物を書き換えない**。  
- 確認結果は **002（再判定）／003（再正規化）／004（再メタ）** へ接続する。**UI 文言・画面の正本は [SPEC-TI-007](../05_experience_quality/SPEC-TI-007-ui.md)**。

---

## スコープ

- 人確認へ**遷移する条件**、**対象の優先順位**、**質問対象の種類**  
- **001／002／003／011** から受け取る情報と **004 の `review_points`** の関係  
- **人に確認させるべき粒度**、**質問方式**・**回答形式**・**回答の保持**  
- **再判定・再正規化の戻し先**（002／003／004／011／013 の区別）  
- **解決状態**（完全／部分／未解消／スキップ／再実行待ち）  
- **IT リテラシーが高くない利用者**への配慮、**未解消時**の扱い  
- **011／013** へ渡す情報、**`HumanReviewSession`**（または同等概念）の**構造方針**  
- **`evidence`／`ambiguity`／`parse_warnings` の受け取りと引き継ぎ**

---

## 非スコープ

- **読取・判定・正規化・分析メタ生成のロジック本体**（001〜004）  
- **信頼度の数式**（011）、**候補生成アルゴリズム**（013）  
- **taxonomy・見出しモデルの正本定義**（009／010／002）  
- **UI 文言全文**（007）、**API／DB 詳細**（014／015）

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 人確認セッション | [SPEC-TI-006 §5.9](../01_foundation/SPEC-TI-006-io-data.md) の `HumanReviewSession`（概念）。 |
| review point | 004 が列挙する**論点 1 条**。005 のキュー要素の**主入力**。 |
| 解消 | 回答により不確実性が減り、上流の**再生成**または**メタ更新**が起きうる状態。 |
| 再実行 | 002／003／004（または 001 起点）の**パイプライン再ジョブ**（014 で詳細化）。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) | **`parse_warnings`・`region_hints`・再読取**の前提。005 は読取しない。 |
| [SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) | **`NEEDS_REVIEW`・`evidence`・`decision`・再判定**の正本。 |
| [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) | **`PARTIAL`／`FAILED`・`skipped_regions`・`incomplete_bindings`** 等の**正規化制約**の参照源。 |
| [SPEC-TI-004](SPEC-TI-004-analysis-metadata.md) | **`review_points` の生成元**・**再メタ**の正本。 |
| [SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) | **解消状態・不確実性**の**特徴量入力**。 |
| [SPEC-TI-013](SPEC-TI-013-suggestion-generation.md) | **候補抑制**前提。005 は抑制**レベル宣言**まで。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | `HumanReviewSession` の**必須フィールド**。 |
| [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) | 人が選ぶ表種別は **009 enum**（002 と整合）。 |
| [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) | 見出し修正は 002／003 経由。005 は木を直接編集しない。 |

### 004 分析メタデータとの接続境界（MVP）

- **005 は** **[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md)** の **`review_points[]`**（および **`review_required`**）を**主な受け取り対象**とする。必要に応じて **003** の **`trace_map[]`**、**`rows[]`**、**`column_slots[]`** および **004** の分析メタ候補を**参照**する。  
- **004** の整理結果を **「完全確定済み」**とはみなさない。**意味確定**の正本分担は上流の各仕様に残し、**005** は**人確認**（質問化・**確認状態**・部分解決／未解消／エスカレーション・**再判定／再正規化／上位仕様**への戻しに使う**レビュー結果保持**）を担う。  
- **005** は**分析意味の正本を新規定義する層ではない**。**011**（信頼度）・**013**（候補）の**最終接続**を壊さない前提とする。  
- 004 側の整理は **[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md)** の「005 人確認フローへの受け渡し（MVP 境界）」を参照。

### Backend MVP API: `mvp_005_canonical_summary`（観測）

- **正本**は引き続き **`HumanReviewSession` 行**、**`SuppressionRecord`**、および snapshot 列（`review_required_snapshot` / `review_points_snapshot`）である。  
- API 応答に含まれる **`mvp_005_canonical_summary`**（`schema_ref`: `ti.mvp_005_canonical_review_summary.v1` 想定）は、上記正本から組み立てる **読み取り専用の観測ブロック**であり、**新たな正本ではない**。自動解決・意味確定を行わない（`semantic_lock_in` は false）。  
- **`unresolved_work_present`** および **`review_state` / `resolution_status` / `resolution_grade` / `suppression_status` / `suppression_record_count` / `uncertainty_intake_present` / `from_004_*`** は、いずれも **005 canonical summary 上で観測される指標**である。**正本そのものではなく**、正本行・snapshot から導いた **派生要約**である。**011 / 013 はこれらを read-only で参照する**（未解決を根拠とした候補昇格・抑制の自動ルール化は MVP では行わない）。  
- OpenAPI の **`TiMvpHumanReviewSession`** と [SPEC-TI-014](../04_system/SPEC-TI-014-api.md) §19 を参照。

### 011 信頼度スコアリングへの受け渡し（MVP 境界）

- **005** の **review 状態**・**解決状態**（**未解消**／**エスカレーション**等）・**残課題**は **011** の **confidence**／**suppression**／**readiness** 判定に**参照されうる**。ただし **005** 自体が**スコア計算**や **suppression の最終決定**を持つわけではない（**011** が正本）。  
- **人確認**の**実施の有無だけ**で機械的に高信頼とは**しない**。**解決度**・**結果内容**・**残課題**を前提に **011** が扱う。**review 済み**でも **未解決**が残る場合は **cautious** な扱いを **011** が**許容**しうる。  
- **部分解消**で重要な曖昧さが残る、**未解消**のまま close、**エスカレーション**、軸衝突の解消／taxonomy・業務意味の残り等は **confidence** の抑制・**caution** 要因になりうる。  
- 011 側の整理は **[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)** の「005 人確認結果との接続境界（MVP）」を参照。

---

## 人確認フローの位置づけ

1. **論点のキューイング**: `review_points[]` を **priority／category** で並べ、**1 論点ずつ**またはバッチで提示する。  
2. **解消パスの選択**: 回答に応じ **002／003／004** のどれを再実行するか決める。  
3. **下流への伝播**: **011**（信頼度）・**013**（候補）が**同じ解消状態**を参照できるようにする。  
4. **境界**: **005＝フローと契約**、**007＝表示**、**011＝スコア**、**013＝候補**。

---

## 入力

### 004 から（主入力・必須）

- **`AnalysisMetadata`** の **`review_required`**、**`review_points[]`**（`point_id`, `category`, `priority`／`severity`, `affected_fields`, `trace_refs`, `suggested_resolution_type` 等、004 定義に準拠）  
- **`table_id`**、**002／003** 成果物への**参照**（005 は中身を再計算しない）

### 001 から（補助）

- **`parse_warnings[]`** — 読取時の**観測事実**・曖昧さ。**再読取**判断の材料。  
- **`region_hints`**（あれば）— タイトル・注記候補と**表本体**の切り分け確認に使う。

### 002 から（補助）

- **`decision === NEEDS_REVIEW`**、**`taxonomy_code`**（未確定・`UNKNOWN` 含む）、**見出し採否の保留**、**`evidence[]`** 内の **`ambiguity`**・**`confidence_hint`**  
- **`evidence[].targets`** — 論点と**セル座標**の対応（001 の座標系と整合）

### 003 から（補助）

- **`normalization_status`**（`PARTIAL`／`FAILED`／`COMPLETE`）、**`skipped_regions[]`**、**`incomplete_bindings[]`**、**`note_blocks[]`**、**`aggregate_rows[]`**、**`type_normalization_notes[]`**（003 の拡張メタに準拠）

### 011 から（任意）

- **`ConfidenceEvaluation`（仮称）**の **`scores`・`explanation`** — **キュー優先度**や**注意喚起**の補助（011 を上書きしない）

### evidence・ambiguity・warnings の扱い

- **`parse_warnings`（001）**: 005 は**改変しない**。**論点説明**・**再読取提案**に**参照**する。  
- **`evidence`／`ambiguity`（002）**: **review point** と**突合**し、**人への説明根拠**として使う。  
- **003 メタ**: **正規化できなかった範囲**を**そのまま**人に見せうる材料として渡す（007 で表現）。

---

## 出力

- **`HumanReviewSession`** の**更新**（§HumanReviewSession の構造方針）  
- **`answers[]`**（概念）— `point_id` 単位の回答履歴（006 MINOR で正式化しうる）  
- **`review_session_resolution_grade`**（概念）— §解決状態の定義、§011／013 への引き継ぎ  
- **`suggestion_suppression_level`**（概念）— §011／013 への引き継ぎ  
- **`human_resolved_uncertainty[]`**（概念）— 解消した **category／point_id** の列挙（011 入力）  
- **`upstream_rerun_plan`**（概念）— 002／003／004 の**再実行リスト**（014 と同期）

---

## 人確認遷移の原則

1. **正本尊重**: 001〜004 の**事実を捏造しない**。確認は**選択・追記・差分**で表す。  
2. **`point_id` 中心**: キューは **004 の `review_points`** で追跡する。  
3. **影響の大きい論点を先に**: 表種別・見出し・単位・grain・主要軸を優先。  
4. **全部解けなくてよい**: **部分解消**を許し、011／013 に**正直に**渡す。  
5. **無理な自動確定禁止**: 未解消は**明示**し、**013 抑制**・**011 減点**の材料にする。

---

## 人確認遷移条件

**標準**: 次を満たすとき**人確認を起動する**（ジョブ側の評価は 014／オーケストレーション）。**主入力シグナル**は **004 の `review_required`／`review_points[]`** である。

| 条件 | 根拠（上流） |
|------|----------------|
| `review_required === true`（004） | 004 |
| `review_points[]` が非空 | 004 |

**暫定・非標準（フェイルセーフ）**: **`AnalysisMetadata` が未生成**などで上表が使えないときのみ、**014** が **`decision === NEEDS_REVIEW`（002）** または **`normalization_status` が `PARTIAL`／`FAILED`（003）** を**直接**起動根拠に**よみがなせる**。**この経路は標準経路ではない**。**速やかに 004 を生成し `review_points` を主入力に戻す**ことを推奨する。

005 は**自ら 002／003 から論点を再構成しない**。**起動済みセッションについて**、005 は**上流の起動条件を再判定しない**。**受理した `review_points`（および紐づくメタ）を処理する**。

---

## 人確認対象の優先順位

**高い順（暫定標準）** — 後続全体に効くものほど先。

1. **表の種類（taxonomy）**の確定  
2. **見出し／表本体の範囲**（どこが格子か）  
3. **見出しの位置・階層**（binding 前提）  
4. **単位**  
5. **grain・主要軸**（004 論点）  
6. **正規化の許容範囲**（003 `PARTIAL`・skipped）  
7. **集計行か明細か**、**注記の扱い**

同順位は **`priority`／`severity`**（004）→ **`point_id` の安定ソート**（暫定）。

---

## 確認対象の分類

004 の **`category`** を**そのまま**分類キーに用いる（005 で新語を増やさない）。**人に聞くべき内容**の例（論点タイプと対応しうる）:

| 確認のねらい | 例（内部ラベル） |
|--------------|------------------|
| **どこが表本体か** | 範囲・bbox・`REGION_ACK` 系 |
| **見出しはどこか** | 行／列見出し、binding 欠落 |
| **表はどの種類に近いか** | taxonomy 単一選択（009 enum） |
| **集計行か明細か** | 行種別の確定 |
| **単位は何か** | 単位競合・スコープ |
| **正規化してよい範囲** | skipped／PARTIAL の許容 |
| **どの仮説を採用するか** | 002 `ambiguity` の枝選択 |

**`suggested_resolution_type`（004）** を**再実行先のヒント**とする（§再判定・再正規化の戻し方）。

---

## 質問方式の方針

**論理タイプのみ**（文言は 007）。

| タイプ ID（概念） | 用途 |
|-------------------|------|
| `SINGLE_CHOICE` | taxonomy・単位・仮説 1 つ |
| `MULTI_CHOICE` | 複数列・複数範囲 |
| `CONFIRM_DENY` | 集計行除外の可否など |
| `FREE_TEXT` | **補足のみ**（主判断は選択肢） |
| `REGION_ACK` | スキップ範囲・対象外の確認 |

**1 画面 1 決定**を推奨。

---

## 回答形式の方針

| 形式 | 下流への載せ方（概念） |
|------|-------------------------|
| **選択肢 ID** | 009 `taxonomy_code` 等 → **002 PATCH** 入力 |
| **列／dimension 指定** | 004 `affected_fields` と整合 → **004 PATCH** |
| **許容／拒否** | 範囲・集計 → **003** フィルタ相当、**004** 更新 |
| **スキップ** | `point_id` **保留**・`SKIPPED_BY_USER` 等 |

---

## 回答結果の保持方針

- **`answers[]`**: **常に `point_id` と生回答**を残し、**監査**に耐える（006 MINOR）。  
- **`HumanReviewSession`**: **state** と **`pending_questions[]`** の更新履歴を残しうる。  
- **上流の新バージョン ID**（`judgment_id`／`dataset_id`／`metadata_id`）を**セッションに紐づけ**る（014）。  
- **原本ハッシュ**（001）との突合はジョブ設計（014／015）。

---

## 再判定・再正規化の戻し方

| 変化の内容 | **戻し先（再実行の正本）** | 011／013 への扱い |
|------------|----------------------------|-------------------|
| 表種別・見出し採否・行種別・列役割 | **002** → 続けて **003→004** が標準 | 再実行後に **011 再評価**、**013 再生成**しうる |
| 縦持ち経路・結合・単位の物理付与 | **003** → **004** | 同上 |
| grain・dimensions／measures の**意味だけ** | **004**（003 再利用可） | **011** はメタ差分を入力、**013** は候補更新 |
| 読取の誤り（セル・範囲） | **001** 起点 → **002→003→004** | 同上 |
| **解消状態・未解消論点の列挙** | **011** へ **`review_session_resolution_grade`・`human_resolved_uncertainty[]`** | **013** へ **`suggestion_suppression_level`・`review_open_count`（補助）** |

**004／011／013 に「引き継ぐもの」**: **004**＝再メタ後の**新 `AnalysisMetadata`** と**残 `review_points`**。**011**＝**解消グレード**・**解消済み category**・**未解消フラグ**。**013**＝**抑制レベル**・**未解消件数**（候補の中身は 013 正本）。

---

## 解決状態の定義

| 状態（概念） | 意味 |
|--------------|------|
| **完全解決** | 意図した必須論点が処理され、**未解消 `point_id` なし**（製品定義の「必須」のみ完了でも可）。`review_session_resolution_grade = FULLY_RESOLVED` に相当。 |
| **部分解決** | **一部**の `point_id` のみ解消。**`PARTIALLY_RESOLVED`**。 |
| **未解消** | 必須論点が残ったまま、または**回答なし**。**`UNRESOLVED`**。 |
| **ユーザースキップ** | 利用者が**明示的にスキップ**。**`SKIPPED_BY_USER`**（`UNRESOLVED` と区別しうる）。 |
| **再実行待ち** | 回答により **002／003／004** がキューされ**完了待ち**。**`WAITING_RERUN`**（セッション `state` の概念）。 |

セッション **`state` の列挙値**と**禁止遷移**の完全固定は **006 Phase4／014**。

---

## ITリテラシー配慮

- **専門用語をそのまま押しつけない**（内部名は 007 で**やさしい言い換え**）。  
- **質問は短く**、**選択肢中心**にできること。  
- **`trace_refs` により原本との対応が見える**こと（ハイライト等は 007）。  
- **間違えてもやり直せる**—「戻る」「やり直し」・**版履歴**は 007／014 で実現。  
- **「わからない」は正当な回答**として定義しうる。

---

## 未解決時の扱い

- **無理に自動確定しない**。  
- **停止または保留**: `CLOSED_UNRESOLVED`・`PARTIALLY_RESOLVED`・`ESCALATED`（運用移管、012／014）を**明示終了**として使う。  
- **005 の責務の限界**: **フローと状態・戻し先の定義**まで。**運用 SLO・エスカレーション手順の全文**は 012／014。  
- **011** へ **未解消・スキップ**を**正直に**渡す。**013** へ **抑制レベル**を渡す。

---

## 011 / 013 への引き継ぎ

**011 へ**: **`review_session_resolution_grade`**（`FULLY_RESOLVED`／`PARTIALLY_RESOLVED`／`UNRESOLVED`／`SKIPPED_BY_USER`）、**`human_resolved_uncertainty[]`**（解消した `point_id`／`category`）、セッション単位の**未解消件数**（特徴量化は 011 正本）。**011 は `suggestion_suppression_level` を確定しない**（抑制に関する**リスク信号・推奨帯**は 011 正本）。

**013 へ**: **`suggestion_suppression_level`**（`SUGGESTION_BLOCKED`／`LIMITED`／`SUGGESTION_ALLOWED_WITH_CAUTION` 等、概念）、**`review_open_count`**（補助）。**`suggestion_suppression_level` の確定値の正本は 005**であり、**013 は必ず尊重**する。**候補の並び・件数・弱化の最終制御は 013**が行い、**011 のスコア・`explanation` を補助材料**として読んでもよい。**013 は 011・005 のオブジェクトを書き換えない**。

---

## HumanReviewSession の構造方針

[SPEC-TI-006 §5.9](../01_foundation/SPEC-TI-006-io-data.md) を満たす。

| フィールド | 005 における意味 |
|------------|------------------|
| `session_id` | 一意 ID |
| `table_id` | 対象表 |
| `state` | §解決状態の定義と整合する**暫定ステート**（`OPEN`／`IN_PROGRESS`／`WAITING_RERUN`／`PARTIALLY_RESOLVED`／`RESOLVED`／`CLOSED_UNRESOLVED`／`ESCALATED` 等） |
| `pending_questions[]` | 未完了の **`point_id`** キュー |

**JSON Schema 完全形**は **006 Phase4**。**`answers[]`** は **006 MINOR** で追加しうる。

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| 画面文言・コンポーネント | SPEC-TI-007 |
| REST／ジョブ・PATCH | SPEC-TI-014 |
| 永続化 | SPEC-TI-015 |
| 信頼度の式 | SPEC-TI-011 |
| 候補ロジック | SPEC-TI-013 |
| `review_points` のスキーマ詳細 | SPEC-TI-004 |
| `HumanReviewSession` の JSON Schema | SPEC-TI-006 Phase4 |

---

## レビュー観点

- **001／002／003／011** の入力が**論点に届いている**か。  
- **遷移条件**と **`review_points`** の**欠落**がないか。  
- **戻し先**（002／003／004 と 011／013）が**誤接続**していないか。  
- **解決状態**が **011／013** に**一貫**して渡るか。  
- **低 IT 配慮**がフロー上**実現可能**か（007 と整合）。

---

## 初版成立ライン

- **遷移条件**・**優先順位**・**確認対象の種類**・**質問／回答形式**が文章化されている。  
- **001／002／003／011** からの**入力**と **`evidence`／warnings** の**引き継ぎ**が明記されている。  
- **再判定・再正規化の戻し先**と **011／013 への引き継ぎ**が区別されている。  
- **解決状態**（完全／部分／未解消／スキップ／再実行待ち）が定義されている。  
- **`HumanReviewSession`** の**構造方針**がある。  
- **004／007／011／013／014** との境界が明確。

---

## 補足メモ（初版の外枠）

### この初版で未確定の論点

- **`state` の正式 enum**と**禁止遷移**の完全列挙（006／014）。  
- **1 セッション複数 `table_id`** の可否。  
- **`suggestion_suppression_level` と 011 スコアの自動連動**の有無。  
- **必須論点と任意論点**の製品定義。

### SPEC-TI-011 に引き継ぐ事項

- **`review_session_resolution_grade` とスコアの合成**、**`human_resolved_uncertainty[]` の重み**。

### SPEC-TI-013 に引き継ぐ事項

- **`suggestion_suppression_level` と `review_open_count`・011 の組合せ**。

### SPEC-TI-001／002／003／004／006／011／013 との自己点検結果

| 観点 | 結果 |
|------|------|
| 001 | **整合**。再読取は 001 へ委譲。 |
| 002 | **整合**。再判定は 002 正本。 |
| 003 | **整合**。再正規化は 003 正本。 |
| 004 | **整合**。`review_points` 主入力。 |
| 006 | **整合**。セッション必須フィールドを尊重。 |
| 011 | **整合**。解消状態を渡すのみ。 |
| 013 | **整合**。抑制前提を渡すのみ。 |

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.2.2 | 2026-04-07 | §関連仕様書に「011 信頼度スコアリングへの受け渡し（MVP 境界）」を追記（解決状態の参照・011 正本・無条件高信頼禁止・011 節への参照）。 |
| 0.2.1 | 2026-04-07 | §関連仕様書に「004 分析メタデータとの接続境界（MVP）」を追記（review_points 主受け・003／004 参照・正本越境なし・011／013 整合・004 節への参照）。 |
| 0.2 | 2026-04-19 | 標準経路と 004 主入力の明確化、暫定トリガの位置づけ、`suggestion_suppression_level` 正本と 011／013 役割。 |
| 0.1 | 2026-04-18 | Draft 初版本文。指定 24 章構成。001／002／003／011 入力、確認対象・戻し先・解決状態・IT 配慮・未解消、011／013 引き継ぎ、HumanReviewSession、evidence／warnings 受け取り。 |
