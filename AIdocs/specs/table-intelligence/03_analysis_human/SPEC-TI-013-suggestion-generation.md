---
id: SPEC-TI-013
title: 分析候補生成仕様書
status: Draft
version: 0.2.2
owners: []
last_updated: 2026-04-08
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-003, SPEC-TI-004, SPEC-TI-005, SPEC-TI-006, SPEC-TI-009, SPEC-TI-010, SPEC-TI-011]
---

## 文書目的

[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md) の **`AnalysisMetadata` を主入力**とし、必要に応じて [SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) の信頼度評価、[SPEC-TI-005](SPEC-TI-005-human-review-flow.md) の review 解消状態・抑制レベルを参照して、**「このデータで何ができるか」を分析候補として提案する**規約の**正本**とする。

**責務の明記**

- **013 は分析候補生成の正本**である。**011 は信頼度・抑制に関するリスク信号／推奨帯の正本**であり、013 は**読む側**であり**上書きしない**。**005 は review 状態および `suggestion_suppression_level` の確定値の正本**（セッション・フロー）であり、**013 は 005 の宣言を必ず尊重**する。**004 は分析意味メタの正本**である。**013 は `suggestion_suppression_level` の正本ではない**。  
- **013 は読取・判定・正規化・メタ生成・人確認・信頼度計算を再実行しない**。  
- **候補の並び・件数・弱化・注意付きの最終制御は 013 が担う**。**`suggestion_suppression_level` については 005 の宣言のみを正とし**、**011 のスコア・`explanation`・推奨帯は補助材料**として読んでもよい。**011 のスコアオブジェクト・005 のセッション成果を書き換えない**。

---

## スコープ

- **SuggestionGeneration（候補生成）の目的と位置づけ**  
- **004 主入力**、**011／005 の参照方法**  
- **候補生成の前提条件**、**候補カテゴリ**（時系列・比較・構成比・ランキング・分布・クロス／相関 等）  
- **`dimensions`／`measures`／`grain`／`time_axis`／`filters`／`available_aggregations` の読み方**  
- **禁止・抑制ルール**、**不適切な候補を出さないためのルール**  
- **候補ごとの根拠説明**・**必要前提条件**（`required_fields` 等）  
- **`review_required`・低信頼時の候補制御**  
- **`SuggestionSet`（または同等概念）の構造方針**  
- **007／011／014 等への委譲境界**

---

## 非スコープ

- **信頼度スコア式**（011）、**人確認 UI・具体質問文**（005／007）  
- **taxonomy・見出しモデルの正本**（009／010／002）  
- **正規化アルゴリズム**（003）、**メタの意味付け本体**（004）  
- **API・DB 物理設計**（014／015）  
- **自然言語プロンプト全文**、**実行エンジン・SQL 生成**

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 分析候補 | 1 つの提案単位。カテゴリ・優先度・根拠・リスク・フォローアップを持ちうる。 |
| SuggestionSet | 1 回の生成 run の成果物（`suggestion_run_id`、`table_id`、候補配列、抑制ログ等）。006 Phase4 で型名を固定しうる。 |
| 抑制 | 候補を**出さない**、**件数を減らす**、**注意ラベル付き**にする制御。 |
| evidence（候補オブジェクト） | **どの 004／011 フィールドに基づくか**を指す参照リスト（根拠説明用）。 |
| confidence（候補オブジェクト） | 当該候補の**成立可能性**（011 の表単位スコアとは別層）。 |
| readiness（候補オブジェクト） | 当該候補を**実行に進める準備度**（必須メタの充足）。 |
| priority（候補オブジェクト） | **提示順**・強調のための優先度。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-004](SPEC-TI-004-analysis-metadata.md) | **主入力 `AnalysisMetadata` の正本**。013 は**再解釈で矛盾しない**。 |
| [SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md) | **信頼度の正本**。013 は**読み取りのみ**。 |
| [SPEC-TI-005](SPEC-TI-005-human-review-flow.md) | **`suggestion_suppression_level`**、review 解消状態の**供給**。013 は**整合**。 |
| [SPEC-TI-003](../02_pipeline/SPEC-TI-003-normalization.md) | **`NormalizedDataset` は補助参照**（列・行の実体・正規化ステータス）。 |
| [SPEC-TI-002](../02_pipeline/SPEC-TI-002-judgment.md) | **`JudgmentResult` は補助参照**（`taxonomy_code`・`decision` の索引）。 |
| [SPEC-TI-001](../02_pipeline/SPEC-TI-001-table-read.md) | **生読取結果を主入力にしない**。004／011 経由の反映に従う。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | 将来 **`SuggestionSet` の JSON Schema 正本**（Phase4）。 |
| [SPEC-TI-009](../01_foundation/SPEC-TI-009-table-taxonomy.md) | **表タイプ語彙**。013 は新ラベルを増やさない。 |
| [SPEC-TI-010](../01_foundation/SPEC-TI-010-heading-model.md) | 見出しの正本。013 は**改変しない**。 |

### Backend MVP API: `generation_constraints_reference`（参照のみ）

- **`GET /suggestion-runs/{suggestion_run_ref}`** の応答に含まれる **`generation_constraints_reference`**（`schema_ref`: `ti.mvp_013_generation_constraints_reference.v1` 想定）は、同一 `metadata` に紐づく **最新 005 セッション**由来の **`primary_constraints_from_005`**（`mvp_005_canonical_summary` と同型の観測）と、**最新 011 評価**由来の **`auxiliary_signals_from_011`** を**読み取り専用**で載せる。**`primary_constraints_from_005`** には **`unresolved_work_present`** 等の **005 未解決観測が含まれうる**。013 は **参照のみ**であり、未解決を根拠に **候補昇格・候補抑制を自動決定しない**（gating 本格化は未着手）。**`GET .../candidates`** も **同系統の read-only 参照面**（トップレベル `generation_constraints_reference`）を持つ。  
- **`auxiliary_signals_from_011`** は、その **`ConfidenceEvaluation` 行**に既に格納されている signal の**写し**である。少なくとも **`evaluation_ref`**（= `evaluation_id`）、**`confidence_score`**、**`decision_recommendation`**、**`risk_signals`** を含む。**`risk_signals`** は **JSON 配列**であり、**要素は object を含みうる**（**string[] 固定ではない**）。013 は**新しい補助 signal を生成しない**（再計算しない）。  
- **`GET /suggestion-runs/{suggestion_run_ref}/candidates`** の応答にも、上記と**同型・同 builder 由来**の **`generation_constraints_reference`** を**トップレベルに**含める（`candidates[]` とは別キー。候補 1 件ごとへの複製はしない）。**候補の確定・suppression 正本の変更は行わない**。  
- **`analysis_candidates[]` / `candidates[]` を本ブロックによって自動変更しない**。**suppression の正本は 005**（`suppression_applied` は 005 を読んだ監査ログ）。**未解決を確定済み候補に昇格させない**。  
- OpenAPI の **`TiMvpSuggestionSet`** / **`listSuggestionCandidates` 200** と [SPEC-TI-014](../04_system/SPEC-TI-014-api.md) §19 を参照。

### Backend MVP: stub `analysis_candidates` の根拠トレース（Pattern B）

- 現行 MVP では **`measures` が非空**なら **1 件**の **`category: summary_stub`** を返し、**空なら 0 件**である。**priority・readiness 等はスタブ的固定**のまま（本格カテゴリ・gating は未着手）。
- 各候補の **`evidence` / `risk_notes`** に **004 `AnalysisMetadata` 観測**（`metadata_id`、`dataset_id`、`dimensions` / `measures` の id・name、`time_axis` の有無等）を **トレースとして**載せうる。**意味確定・taxonomy 確定・semantic lock-in ではない**。
- **005 / 011 は候補の採否・順位決定に使わない**（read-only は **`generation_constraints_reference`** の GET 応答のみ。§19・014 §19.5 参照）。

### 011 信頼度スコアリングとの接続境界（MVP）

- **013 は** **[SPEC-TI-005](SPEC-TI-005-human-review-flow.md)** の **`suggestion_suppression_level`**・**review** 結果を**一次制約**として**尊重**しつつ、**[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)** の **confidence**／**readiness**／**caution** を**補助入力**として**参照しうる**。**011** の数値・状態**だけ**で機械的に採択を**確定**せず、**011** を参照しても **005** の **suppression** を**上書きしない**。  
- **013** は**候補の提示可否**・**優先度**・**注意付き提示**・**限定提示**を整理するが、**review 状態**や **confidence** を**新規定義する層ではない**。**未解決**を**確定済み候補**として**押し出さない**。  
- **caution**／**limited**／**blocked** 相当の扱いは **007** 等**上位仕様**に渡す際も**壊さない**前提とする。**004** の分析メタ**候補**とも**整合**する。  
- 011 側の整理は **[SPEC-TI-011](../02_pipeline/SPEC-TI-011-confidence-scoring.md)** の「013 分析候補生成への受け渡し（MVP 境界）」を参照。

---

## 候補生成の位置づけ

1. **合成**: 004 の意味付けを**主**に、**005 の `suggestion_suppression_level`（制約の正本）**と **011 の信頼度・信号（補助）**を**ゲート**として候補集合を生成する。  
2. **価値提示**: 利用者が分析仮説を持たない場合でも**有益な切り口**を列挙する。  
3. **ゲーティング**: `review_required`・`suggestion_suppression_level`・低信頼を**無視しない**。  
4. **下流接続**: 各候補は**実行方針**（クエリ種別・必須フィールド）へマッピングしうる情報を持つ。  
5. **再実行禁止**: 上流ジョブ（001〜005・011 の計算）を 013 内で再走させない。

---

## 入力

### 主入力（必須）

- **`AnalysisMetadata`**（[SPEC-TI-004](SPEC-TI-004-analysis-metadata.md)）  
  - 少なくとも **`metadata_id`**, **`dataset_id`**, **`grain`**, **`dimensions[]`**, **`measures[]`**  
  - 利用しうる拡張: **`time_axis`**, **`category_axes[]`**, **`filters[]`**, **`available_aggregations[]`**, **`inferred_business_meaning`**, **`metadata_confidence_hints`**, **`review_required`**, **`review_points[]`**

### 補助参照（必要に応じて）

- **`NormalizedDataset`**（003）— **列の実在・欠損・cardinality・`normalization_status`** 等を**004 と矛盾なく**確認するときのみ。  
- **`JudgmentResult`**（002）— **`taxonomy_code`（009 enum）**, **`decision`** を**表タイプ別ルールの索引**に使うとき。  
- **`ConfidenceEvaluation`（011 で定義される出力）**— 表単位スコア、`explanation`、011 が付す **`suggestion_suppression_level` 参考値**（**005 が宣言している場合は 005 を採用**）。

### 主入力に含めないもの

- **`TableReadArtifact`（001 の生読取結果）を 013 の主入力としない**。観測事実は **004／003 経由**で間接的にのみ効く。

### 005 からの参照（セッション・状態）

- **`suggestion_suppression_level`**（005 の概念）  
- **未解消 `review_points`**, **`review_session_resolution_grade`**（005／セッションスナップショット）

---

## 出力

- **`SuggestionSet`**（§SuggestionSet の構造方針）— 少なくとも **`suggestion_run_id`**, **`table_id`**, **`analysis_candidates[]`**  
- **`suppression_applied[]`** — 抑制理由の**監査用ログ**（理由コード・要約）  
- **`regeneration_context`**（任意）— 再生成時の入力差分メモ

---

## 候補生成の原則

1. **004 非矛盾**: `grain`・`dimensions[]`・`measures[]` と**論理矛盾する候補を出さない**。  
2. **011 非侵襲**: スコア・`explanation` を**書き換えない**。**読み取りのみ**。  
3. **005 非侵襲**: review 状態・抑制レベルの**正本を書き換えない**。**参照して候補を制御する**。  
4. **`available_aggregations` 順守**: 004 が許可しない集計を**候補の前提に含めない**。  
5. **説明責任**: 各候補に **evidence**（004／011 のフィールド参照）を付す。  
6. **未確定の明示**: 仮説的候補には **risk_notes**・**followup_questions** を付しうる。

---

## 候補生成の前提条件

次を**順に確認**し、欠ける場合は §候補の抑制条件・各カテゴリ節に従う。

| 前提 | 内容 |
|------|------|
| **measure の有無** | **`measures[]` が空でない**こと。空なら**集計・比較・構成・ランキング・多くの分布・相関**を**原則出さない**。 |
| **time axis の有無** | **`time_axis`（または時間意味を持つ dimension）**が**宣言**されていること。**時系列候補**の必要条件。 |
| **category axis の有無** | **`category_axes[]` または切片に使える dimension** が**複数／単一**で存在すること。**比較・構成・クロス**の可否に効く。 |
| **`available_aggregations` の整合** | 候補カテゴリが要求する集計（`sum`/`avg`/`count` 等）が **004 の許容集合に含まれる**こと。 |
| **`review_required`** | **真**のときは §review_required / confidence / suppression の反映に従い**件数・種類を制限**しうる。 |
| **信頼度** | **011 の表単位スコアが低い**とき、**仮説系・行動系**候補を**弱めるまたは出さない**。 |

---

## 候補カテゴリの定義

**カテゴリ ID**（機械可読。表示ラベルは 007）。

| category ID | 説明 | 対応節 |
|-------------|------|--------|
| `trend_analysis` | 時系列に沿った推移・トレンド | §時系列系候補の生成方針 |
| `comparison_analysis` | 期間・セグメント・カテゴリ間の比較 | §比較系候補の生成方針 |
| `composition_analysis` | 構成比・内訳・割合 | §構成比・割合系候補の生成方針 |
| `ranking_analysis` | ランキング・上位／下位 | §ランキング系候補の生成方針 |
| `distribution_analysis` | 分布・ばらつき・要約統計 | §クロス分析・相関・分布系候補の生成方針 |
| `correlation_hypothesis` | 相関・関係性の**仮説**（確定ではない） | §同上 |

**拡張カテゴリ**（0.1 では概要のみ、詳細ルールは後版で拡張しうる）: `summary_report`, `anomaly_detection`, `segmentation`, `faq_seed_generation`, `action_suggestion` — **いずれも 004／011／005 のゲーティングを同一視する**。

**`taxonomy_code`（002／009）** により**推奨カテゴリの重み**を変えうる（LIST_DETAIL は集計系、TIME_SERIES は時系列優先等）。詳細は各生成方針と §候補の抑制条件に従う。

---

## 時系列系候補の生成方針

| 項目 | 内容 |
|------|------|
| **生成条件** | **`time_axis` が利用可能**、**`measures[]` が非空**、**`available_aggregations` に時系列分析に必要な集計**（例: `sum`/`avg`/`count`）が**含まれる**。 |
| **必要な metadata** | **`time_axis`**（粒度・系列対応）、**主 measure**、**`grain`**（1 行の意味と矛盾しない解釈）、**`filters[]`**（期間制約があれば母集団定義に利用）。 |
| **抑制条件** | **時間軸が曖昧**（004 で未確定・`review_points` が time 関連）、**`review_required === true`** で未解消、**`suggestion_suppression_level` が高い**、**011 低スコア**、**`trend_analysis` 用集計が `available_aggregations` にない**。 |

---

## 比較系候補の生成方針

| 項目 | 内容 |
|------|------|
| **生成条件** | **比較軸**として **2 つ以上の切片**または**2 期間以上**が**論理可能**（**`category_axes[]`** または **複数 dimension** ＋ **`time_axis`**）。**measure が非空**。 |
| **必要な metadata** | **`dimensions[]`／`category_axes[]`**, **`measures[]`**, **`time_axis`**（期間比の場合）、**`filters[]`**, **`grain`**, **`available_aggregations`**。 |
| **抑制条件** | **軸が 1 つしかない**かつ **時期分割も定義できない**、**単位競合**、**`review_required`** かつ軸系論点が未解消、**suppression 高**、**許容集計が比較に不十分**。 |

---

## 構成比・割合系候補の生成方針

| 項目 | 内容 |
|------|------|
| **生成条件** | **分母が `grain`・`filters` と整合**して定義できる。**名義軸**（**`category_axes[]`** 等）と **measure**（または **count**）が揃う。**`available_aggregations` に `sum`／`count` 等、構成比の母集団定義に必要な集計**が含まれる。 |
| **必要な metadata** | **`category_axes[]` または切片 dimension**, **`measures[]`**, **`grain`**, **`filters[]`**, **`available_aggregations`**, **`aggregate_rows[]` 等の 003 メタが 004 に反映されている場合はその扱い**（二重集計回避）。 |
| **抑制条件** | **分母未定義**・**集計行が母集団に未分離**、**`PARTIAL`／`FAILED` で母集団が不明**、**構成比に必要な集計が許容リストにない**、**review／suppression／低信頼**。 |

---

## ランキング系候補の生成方針

| 項目 | 内容 |
|------|------|
| **生成条件** | **順位付け可能な measure**、**切片軸**（**dimension／category**）が**少なくとも 1 つ**、**`available_aggregations` に `sum`／`avg`／`count` 等、ランキングに使う集計**が含まれる。 |
| **必要な metadata** | **`measures[]`**, **`dimensions[]`／`category_axes[]`**, **`grain`**, **`filters[]`**, **`available_aggregations`**。 |
| **抑制条件** | **measure が空**、**同順位の多重度が解釈不能**、**集計行混入未解決**、**review／suppression／低信頼**、**許容集計不足**。 |

---

## クロス分析・相関・分布系候補の生成方針

### 分布・ばらつき（`distribution_analysis`）

| 項目 | 内容 |
|------|------|
| **生成条件** | **数値 measure が存在**、**十分な行数**（003 の行集合で解釈可能）、**`available_aggregations`** に **分布説明に使う集計**（`min`/`max`/`avg`/`count` 等）が**含まれる**。 |
| **必要な metadata** | **`measures[]`**, **`grain`**, **`filters[]`**, **`available_aggregations`**。 |
| **抑制条件** | **行数極小**、**単位不明**、**`grain` 不明確**、**review／suppression／低信頼**。 |

### クロス分析・相関仮説（`correlation_hypothesis` 等）

| 項目 | 内容 |
|------|------|
| **生成条件** | **2 つ以上の数値 measure**、または **数値＋切片**の組合せが **004 上**解釈可能。**仮説カテゴリ**として扱い**確定分析とラベルを混同しない**。 |
| **必要な metadata** | **複数 `measures[]`** または **measure＋dimension**, **`grain`**, **`available_aggregations`**。 |
| **抑制条件** | **measure が 1 つのみで相関の意味が成立しない**、**名義のみで数値がない**、**`review_required` 真**（仮説系は**特に抑制**）、**011 低スコア**、**suppression 高**。 |

**`category_axes` と `time_axis` の直交**は 004 に従い、**競合する候補は出さない**か **risk_notes 必須**とする。

---

## 候補の抑制条件

次のいずれかに該当するとき、**候補を出さない**、**カテゴリを禁止**、または **注意付き（低優先・risk_notes 必須）**にする。

| 条件 | 方針 |
|------|------|
| **`review_required === true`** | **件数削減**、**仮説系・行動系の禁止または弱化**、残りは **WARNING 相当の提示**（007 が表現）。 |
| **`suggestion_suppression_level` が高い**（005） | **`SUGGESTION_BLOCKED` に近い**ときは**候補ゼロまたは極小**。**`LIMITED`** は**安全カテゴリのみ**（例: 要約・FAQ 系があれば限定）。 |
| **信頼度が低い**（011） | **表単位スコアが低い**とき **仮説・異常・行動**系を**抑制**。**全候補の confidence 上限**を下げうる。 |
| **`available_aggregations` に含まれない集計** | その集計を要する**候補を出さない**。 |
| **`grain` が不明確** | **解釈を要する集計・比較・構成比**を**抑制**。 |
| **`measures[]` が空** | **集計依存カテゴリを出さない**（**補助的カテゴリのみ**可）。 |
| **集計行・単位競合が未解決**（004／003 経由） | **sum／avg 系**を**抑制**。 |

---

## review_required / confidence / suppression の反映

- **`review_required`**: 004 のフラグを**最優先のゲート**の一つとする。**真**のときは §候補の抑制条件・各カテゴリの**抑制条件**を**厳しく適用**する。  
- **confidence（011）**: **011 は信頼度の正本**。**013 は参照**し、**閾値以下**では候補数・カテゴリを**削る**。**011 を再計算しない**。  
- **`suggestion_suppression_level`（005）**: **確定値の正本は 005**。**013 は必ず尊重**し、**自ら別の suppression 正本を立てない**。011 が推奨帯を出していても、**矛盾時は 005 を正**とする。  
- **並び・最終制御**: **013 が候補リストの並びと「出す／出さない」を最終的に組み立てる**。**011 のスコア・`explanation` は補助材料**。**011 のスコアオブジェクト・005 のセッション正本を改変しない**。

---

## 根拠説明の方針

各候補は**少なくとも**次を**機械可読**に持ちうる（文言テンプレは 007）。

- **なぜ出せるか**: **`evidence[]`** — 参照した **004 のフィールドパス**（例: `004.time_axis`, `004.measures[]`）および **011 の因子／スコア参照**（例: `011.scores.table`）。  
- **どの metadata に基づくか**: **`required_fields`**, **`optional_fields`**（論理パス表記。例: `measures.amount`, `time_axis.month`）。  
- **どの前提が未確定か**: **`risk_notes[]`**（単位監視中、期間定義の保留等）、**`followup_questions[]`**（候補実行後に足りない情報）。**005 の review 論点**と**目的が異なる**（005＝上流不確実性解消、013＝候補活用の確認）。

---

## SuggestionSet の構造方針

| 要素 | 説明 |
|------|------|
| `suggestion_run_id` | 一意 ID。 |
| `table_id` | 対象表。 |
| `analysis_candidates[]` | 候補オブジェクトの配列。 |
| 候補オブジェクト（概念） | `candidate_id`, `category`, `priority`, `confidence`, `readiness`, `required_fields[]`, `optional_fields[]`, `evidence[]`, `risk_notes[]`, `followup_questions[]`, `presentation_hint`（007 向け）等。 |
| `suppression_applied[]` | **抑制理由**の監査ログ（コード・要約）。 |

**JSON Schema 完全形**は **006 Phase4**。**同一入力での再現性**（LLM 使用時は別途方針）は **014／製品**で固定しうる。

**出力例（構造イメージのみ）**:

```json
{
  "suggestion_run_id": "sg-run-01",
  "table_id": "tbl-1",
  "analysis_candidates": [
    {
      "candidate_id": "cand-001",
      "category": "trend_analysis",
      "priority": 0.8,
      "confidence": 0.7,
      "readiness": 0.75,
      "required_fields": ["measures.amount", "time_axis.month"],
      "optional_fields": ["dimensions.region"],
      "evidence": ["004.time_axis", "004.measures", "011.scores.table"],
      "risk_notes": [],
      "followup_questions": []
    }
  ],
  "suppression_applied": []
}
```

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| 画面・コンポーネント・文言 | SPEC-TI-007 |
| 人確認フロー・PATCH・セッション | SPEC-TI-005 |
| 信頼度の式・閾値・`ConfidenceEvaluation` スキーマ | SPEC-TI-011 |
| `AnalysisMetadata` の意味・許容集計の宣言 | SPEC-TI-004 |
| API・ジョブ・再生成トリガ | SPEC-TI-014 |
| DB | SPEC-TI-015 |
| `SuggestionSet` の JSON Schema | SPEC-TI-006 Phase4 |

---

## レビュー観点

- **`AnalysisMetadata` を主入力**とし、**001 を直接主入力にしていない**か。  
- **004 の `grain`・`available_aggregations` と矛盾する候補**を出していないか。  
- **011 を上書き**していないか。**005 の suppression** と**実際の候補**が矛盾していないか。  
- **各カテゴリ**について **生成条件／必要 metadata／抑制条件**が**本文で追える**か。  
- **根拠説明**（evidence・required_fields・未確定）が**候補単位**で説明可能か。

---

## 初版成立ライン

- **`AnalysisMetadata` 主入力**、**003／002 は補助**、**001 非主入力**が明記されている。  
- **前提条件**（measure・time・category・aggregations・review・信頼度）が整理されている。  
- **時系列・比較・構成比・ランキング・分布・クロス／相関**の**方針表**がある。  
- **抑制条件**と **review／confidence／suppression の反映**が明記されている。  
- **`SuggestionSet` の構造方針**と **011／005／007／014 への委譲**がある。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.2.1 | 2026-04-07 | §関連仕様書に「011 信頼度スコアリングとの接続境界（MVP）」を追記（005 正本・011 補助・未解決の確定扱い禁止・011 節への参照）。 |
| 0.2 | 2026-04-19 | 005 を suppression 確定正本、011 を補助信号、013 を最終制御実行者と明文化。位置づけ・反映節の整合。 |
| 0.1 | 2026-04-18 | Draft 初版本文。指定 23 章構成。004 主入力、カテゴリ別生成／抑制、011 読取・005 suppression、SuggestionSet、根拠説明。 |
