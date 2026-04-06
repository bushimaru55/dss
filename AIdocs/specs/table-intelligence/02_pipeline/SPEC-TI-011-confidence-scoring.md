---
id: SPEC-TI-011
title: 信頼度スコアリング仕様書
status: Draft
version: 0.3
owners: []
last_updated: 2026-04-19
depends_on: [SPEC-TI-001, SPEC-TI-002, SPEC-TI-003, SPEC-TI-004, SPEC-TI-005, SPEC-TI-006]
---

## 文書目的

[SPEC-TI-001](SPEC-TI-001-table-read.md)〜[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md) のパイプライン成果（観測・判定・正規化・分析メタ・人確認）を入力とし、**表解析結果をどの程度信頼してよいか**を表す**信頼度スコアリングの正本**を定義する。

**明記（責務の正本）**

- **[SPEC-TI-001](SPEC-TI-001-table-read.md)** は **観測**の正本、**002** は **判定**、**003** は **変換**、**004** は **意味メタデータ**、**005** は **人確認フロー**の正本であり、**011 は信頼度評価**の正本である。  
- **011 は読取・判定・正規化・分析メタ生成・人確認を再実行しない**。各段階の**出力を特徴量として読み**、**スコアと説明**を生成する。  
- **[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md)** の **`review_session_resolution_grade`** および **`human_resolved_uncertainty[]`**（概念）は **011 の重要入力**である。  
- **004** の `review_required`／`review_points`、**003** の `PARTIAL`／`FAILED` 等、**002** の `decision`／`evidence`、**001** の `parse_warnings` は **特徴量**となる。  
- **011 はスコア値・閾値・説明構造の正本**である。**抑制を強めるべき信号**や**スコア帯に基づく推奨**も 011 が**説明付きで**出しうる（**`suggestion_suppression_level` の確定値の正本は 005**であり、**011 はそれを直接確定しない**）。**013 は 005 の宣言を必ず尊重**しつつ、**011 の信号を補助材料**として候補の並び・件数・弱化を**最終制御**する。**011 は 013 を上書きせず**、**013 も 011 のスコアオブジェクトを書き換えない**。  
- **011 は explanation 可能**であること。加点／減点要因を**説明オブジェクト**に落とし、**002 の evidence** および **005 の解消状態**と**参照で接続**できる。

---

## スコープ

- **信頼度スコアリングの対象**（どの単位にスコアを付けるか）
- **スコアの粒度**と**上位集約**（候補生成向け）
- **入力特徴量**の整理（001〜005）
- **加点要因**・**減点要因**（暫定。数式の完全固定は初版では必須としない）
- **review 解消状態**の反映（`FULLY_RESOLVED` 等）
- **`PARTIAL`／`FAILED`／`UNKNOWN`／`NEEDS_REVIEW`** の扱い
- **スコアと `decision`（002）**の関係（再解釈）
- **スコアと suggestion 抑制**（005／013）の関係
- **evidence／explanation** との関係
- **011 の出力**の方針（006 MINOR でエンティティ化しうる）

---

## 非スコープ

以下は**詳細確定しすぎない**。委譲先を明記する。

- **読取・判定・正規化・意味メタ生成のロジック**（001〜004）  
- **人確認フローそのもの**（[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md)）  
- **分析候補生成アルゴリズム**（[SPEC-TI-013](../03_analysis_human/SPEC-TI-013-suggestion-generation.md)）  
- **UI の具体文言・見た目**（[SPEC-TI-007](../05_experience_quality/SPEC-TI-007-ui.md)）  
- **API／DB 物理設計**（[SPEC-TI-014](../04_system/SPEC-TI-014-api.md)／[SPEC-TI-015](../04_system/SPEC-TI-015-db.md)）

---

## 用語定義

| 用語 | 説明 |
|------|------|
| 信頼度スコア | **数値または正規化レンジ**（例: 0–1 または 0–100）。**閾値**で `decision` 再解釈や UI 表示に使う（本書が正本）。 |
| 特徴量 | 各ステージ出力から抽出した**スコア入力**（カウント、フラグ、列挙の強度等）。 |
| explanation | **人が読める**短い理由リスト。**加点／減点要因**と **上流 ID**（`rule_id`・`point_id` 等）への参照を含みうる。 |
| 集約スコア | **table 単位**または**ジョブ単位**に、下位スコアを**合成**した値（013・UI 向け）。 |

---

## 関連仕様書との関係

| 仕様 | 関係 |
|------|------|
| [SPEC-TI-001](SPEC-TI-001-table-read.md) | `parse_warnings` 等の**観測特徴量**の供給源。 |
| [SPEC-TI-002](SPEC-TI-002-judgment.md) | 一次 `decision`・`evidence`・`confidence_hint`。011 が**再解釈**しうる。 |
| [SPEC-TI-003](SPEC-TI-003-normalization.md) | `normalization_status`・binding 欠落・型ノート等の**不確実性**。 |
| [SPEC-TI-004](../03_analysis_human/SPEC-TI-004-analysis-metadata.md) | `review_required`・`review_points`・`metadata_confidence_hints`・inferred の弱さ。 |
| [SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md) | **`review_session_resolution_grade`**・**`human_resolved_uncertainty[]`**・**`suggestion_suppression_level`**（005 が宣言する前提と**整合**）。 |
| [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) | 将来 **`ConfidenceScore`** 等のエンティティ（Phase4）。初版は**概念出力**。 |
| SPEC-TI-013 | スコアを**抑制・注意付け**の**入力**とする。 |

---

## 信頼度スコアリングの位置づけ

表解析パイプラインにおいて、011 は次に限定する。

1. **読むだけ**: 001〜005 の**確定済み出力**を入力とし、**副作用のない評価**を主とする（再実行はトリガしない）。  
2. **説明責任**: スコアの**内訳**を explanation に落とす。  
3. **ゲーティング支援**: 002 の `decision` を**機械的に上書きしうる**（閾値・ポリシーは本書＋製品）。**005 後**は**解消状態**を強く反映する。  
4. **013 連携**: **低スコア**と **005 の `suggestion_suppression_level`** を**矛盾なく説明**しうる。**候補集合の最終制御は 013**。**`suggestion_suppression_level` の確定は 005**。

**境界の再掲**: **005＝抑制レベル（制約）の正本**、**011＝信頼度・リスク信号・推奨の正本**、**013＝候補制御の実行者**、**007＝表示**。

---

## 入力

### 必須（概念）

- **`table_id`**  
- **`JudgmentResult`**（002）— `decision`, `taxonomy_code`, `evidence[]`  
- **`NormalizedDataset`** 参照（003）— `normalization_meta`（`PARTIAL`／`FAILED` 等）  
- **`AnalysisMetadata`**（004）— `review_required`, `review_points[]`, 推奨拡張（`metadata_confidence_hints` 等）  
- **`HumanReviewSession`** またはその**スナップショット**（005）— **`review_session_resolution_grade`**, **`human_resolved_uncertainty[]`**, **`suggestion_suppression_level`**（あれば）

### 推奨

- 001 **`parse_warnings[]`**（件数・重大度タグ）  
- 002 **`evidence[].confidence_hint`**／`details`  
- 003 **`normalization_status`**（`PARTIAL`／`FAILED`／`COMPLETE`）、**`skipped_regions[]`**、**`incomplete_bindings[]`**、**`type_normalization_notes[]`**  
- 004 **`review_required`**、**`review_points[]`**、**`metadata_confidence_hints`**、**`inferred_business_meaning`**（有無・弱さ・空）

---

## 出力

### 主成果物（概念・006 Phase4 でエンティティ化）

初版では **006 を壊さない**ため、次を **`ConfidenceEvaluation`（仮称）** として定義する。

| フィールド（概念） | 説明 |
|--------------------|------|
| `evaluation_id` | 一意 ID。 |
| `table_id` | 対象。 |
| `scores` | **複数粒度**のスコア（§スコア対象の粒度）。 |
| `decision_recommendation` | 002 `decision` との**整合**または**再提案**（`AUTO_ACCEPT`／`NEEDS_REVIEW`／`REJECT`）。**確定はジョブ／製品**（暫定）。 |
| `explanation` | §evidence／explanation との関係。 |
| `feature_snapshot_hash` | 入力特徴量の**再現性**（任意）。 |

### 副次出力

- **013 向け**: **集約信頼度**・**抑制ヒント**（`suggestion_suppression_level` との**整合チェック**結果）。  
- **007 向け**: 表示用の**短いラベル**（文言は 007）。

### 011 の出力方針

- **主出力**は **`ConfidenceEvaluation`（仮称）**: `scores`（複数粒度）、`decision_recommendation`、`explanation`、識別子（`evaluation_id`, `table_id`）。  
- **006 Phase4** まで JSON Schema は [SPEC-TI-006](../01_foundation/SPEC-TI-006-io-data.md) に委譲し、初版は**概念フィールド**に留める。  
- **再現性**: 同一入力スナップショットなら同一スコアとなるよう、特徴量に **`feature_snapshot_hash`（任意）** を付けうる。  
- **副作用なし**: 011 の出力は**下流の状態を書き換えない**（014／ジョブが永続化する）。

---

## スコアリングの原則

1. **非再実行**: パイプラインを 011 内で再走させない。  
2. **証跡接続**: explanation は **002 `rule_id`**, **004 `point_id`**, **001 warning code** 等に**リンク**しうる。  
3. **単調性の目安**: **致命的欠陥**（001 破綻・002 REJECT 相当）は**上限キャップ**しうる（暫定）。  
4. **人確認後優先**: **`FULLY_RESOLVED`** は**減点の打ち消し／回復**を強く許容（§review 解消状態）。  
5. **013 非侵襲**: 011 は **013 の候補を直接削除しない**。**スコアと抑制レベル**で**材料**を渡す。  
6. **透明性**: **同じ特徴量**なら**同じスコア**（再現性。LLM を使う場合は別 SPEC）。

---

## スコア対象の粒度

| 粒度 | 説明 | 主な用途 |
|------|------|----------|
| **table（TableCandidate）** | 1 表候補あたり 1 つの**主スコア**。 | ジョブ全体・一覧画面。 |
| **metadata（AnalysisMetadata）** | メタ生成結果の**信頼度**。 | grain・軸の信頼。 |
| **review_point** | `point_id` ごとの**部分スコア**（任意）。 | 005 の論点別の残リスク表示。 |
| **集約（suggestion 向け）** | 上記を**重み付き合成**した**上位 1 数値またはバンド**。 | **013** の抑制・注意付け。 |

**暫定**: 初版成立ラインは **table 単位＋集約**を必須、**review_point 単位**は任意。

---

## 特徴量一覧

| ソース | 特徴量候補（例） |
|--------|------------------|
| **001** | `parse_warnings` **件数**、**重大度**、特定 code の有無。 |
| **002** | `taxonomy_code` が **UNKNOWN** か、**`NEEDS_REVIEW`** か、`evidence` **件数**・**`confidence_hint`**、**曖昧性**ブロックの有無。 |
| **003** | **`normalization_status`**（**`PARTIAL`**／**`FAILED`**／`COMPLETE`）、**`skipped_regions[]`**（件数・理由コード）、**`incomplete_bindings[]`**（件数）、**`type_normalization_notes[]`**（パース失敗・単位競合等）。 |
| **004** | **`review_required`**、**`review_points[]`**（件数・最大 severity・category）、**`metadata_confidence_hints`**、**`inferred_business_meaning`**（有無・弱さ・空）。 |
| **005** | **`review_session_resolution_grade`**、**`human_resolved_uncertainty[]`**（解消済み category）、**未解消**／**`SKIPPED_BY_USER`** フラグ、**`suggestion_suppression_level`**（**整合検証**の入力）。 |

---

## 加点要因

**数値は初版では固定しない**。**方向性**のみ例示する。

- 002 で **`AUTO_ACCEPT`** かつ **evidence が一貫**、**UNKNOWN でない** taxonomy。  
- 003 で **`COMPLETE`**、binding 欠落なし、型ノート少ない。  
- 004 で **`review_required === false`** または **review_points 空**。  
- 005 で **`FULLY_RESOLVED`**、**human_resolved_uncertainty** が主要 category を**カバー**。  
- 001 warnings **軽微のみ**。

---

## 減点要因

- 001 **致命 warning**・**矛盾**の疑い。  
- 002 **`NEEDS_REVIEW`**、**UNKNOWN taxonomy**、**evidence の競合**。  
- 003 **`PARTIAL`／`FAILED`**、**`skipped_regions[]`** が広い、**`incomplete_bindings[]`**、**`type_normalization_notes[]`** に基づく型・単位の問題の多さ。  
- 004 **`review_points` 多数**・**高 severity**、**inferred 不在**による説明欠落。  
- 005 **`UNRESOLVED`／`SKIPPED_BY_USER`**、**`PARTIALLY_RESOLVED`** で残論点が分析に直撃。

---

## review 解消状態の反映方針

[SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md) の **`review_session_resolution_grade`** に応じ、**人確認前の減点**を**回復**しうる（暫定ポリシー）。

| grade | 反映（暫定） |
|-------|----------------|
| **`FULLY_RESOLVED`** | **review 起因の減点を大幅に相殺**。残るのは 001〜003 の**純技術的不確実性**のみ。 |
| **`PARTIALLY_RESOLVED`** | **一部のみ回復**。残 **`review_points`** に比例して減点残存。 |
| **`UNRESOLVED`** | **人確認で解消なし**。004／005 由来の減点を**維持**。 |
| **`SKIPPED_BY_USER`** | **`UNRESOLVED` より軽い／同等**は製品選択。**明示スキップ**は explanation に記録。 |

**`human_resolved_uncertainty[]`**: 解消済み **category** ごとに、対応する**減点項を打ち消し**うる（マッピング表は Phase2 で拡張）。

---

## PARTIAL／FAILED／UNKNOWN／NEEDS_REVIEW の扱い

| 信号 | スコア上の扱い（暫定） |
|------|-------------------------|
| **003 `PARTIAL`** | **中〜大の減点**。`COMPLETE` との差を explanation に明示。 |
| **003 `FAILED`** | **強い減点**または**スコア上限キャップ**（表として使えないに近い）。 |
| **002 `TI_TABLE_UNKNOWN`** | taxonomy **不確実**として減点（005／004 と組み合わせ）。 |
| **002 `NEEDS_REVIEW`** | **減点**。005 後に **`FULLY_RESOLVED`** なら相殺しうる。 |
| **002 `REJECT`** | **最低帯**または**評価対象外**（ジョブが止まる場合あり）。 |

---

## score と decision の関係

- **002 の `decision` は一次結論**（002 正本）。011 は **スコアと閾値**で **`decision_recommendation`** を出しうる（**上書きルール**は製品・014）。  
- **整合ルール（暫定）**: スコアが**極端に低い**のに `AUTO_ACCEPT` のとき **`NEEDS_REVIEW` 推奨**、など。  
- **011 は decision の唯一の正本ではない**。**衝突**時はログ・explanation に残す。

---

## score と suggestion suppression の関係

- **`suggestion_suppression_level` の確定値の正本は [SPEC-TI-005](../03_analysis_human/SPEC-TI-005-human-review-flow.md)（005）**である。**011 はこのレベルを確定しない**。  
- **011 は**、集約スコア等に基づき、**抑制を強めるべきであることの信号**や、**`suggestion_suppression_level` に相当する帯への推奨**を **explanation に載せうる**（**人間・監査・013 への補助**）。**005 が宣言したレベルと矛盾する場合**は **explanation に両方を記録**する。  
- **[SPEC-TI-013](../03_analysis_human/SPEC-TI-013-suggestion-generation.md) は、`suggestion_suppression_level` については 005 の宣言のみを正とし、011 の信号を補助材料として読み、候補の並び・件数・弱化を最終制御する。** **011 は 013 を上書きせず**、**013 も 011 のスコアオブジェクトを書き換えない**。  
- **暫定マッピング（例・推奨帯。確定ではない）**  

| 集約スコア帯（例） | 推奨 `suggestion_suppression_level` |
|--------------------|--------------------------------------|
| 高 | `SUGGESTION_ALLOWED_WITH_CAUTION` 以下 |
| 中 | `SUGGESTION_LIMITED` |
| 低 | `SUGGESTION_BLOCKED` しうる |

---

## evidence／explanation との関係

- **explanation** は **構造化リスト**（概念）: 各要素に `factor`（加点／減点）、`weight`（任意）、`source`（`STAGE_001`…`STAGE_005`）、`refs`（`rule_id`／`point_id`／warning code）。  
- **002 `evidence[]`** は **そのまま複写せず**、**参照**で結び、説明に**要約**を載せる。  
- **005 の解消状態**は explanation の**トップレベル**に **1 行要約**しうる（例: 「人確認: 主要論点は解消済み」）。

---

## 他仕様書へ委譲する事項

| 内容 | 委譲先 |
|------|--------|
| 人確認の手順・状態遷移 | SPEC-TI-005 |
| 候補の内容・並び | SPEC-TI-013 |
| 画面表示・文言 | SPEC-TI-007 |
| HTTP・ジョブ・永続化 | SPEC-TI-014／015 |
| `ConfidenceEvaluation` JSON Schema | SPEC-TI-006 Phase4 |

---

## レビュー観点

- **特徴量**が 001〜005 で**取りこぼしなく**説明できるか。  
- **解消状態**がスコアに**一貫**して効くか。  
- **decision 再解釈**が 002 と**矛盾しない**か（衝突時のログ）。  
- **013 抑制**との**二重管理**になっていないか（役割分担）。  
- **explanation** が監査に耐えるか。

---

## 初版成立ライン

Draft **0.1** で定義した以下の条件は、現行 **0.2** でも維持する。

- **入力**が 001〜005 の**既存成果物**に限定される**方針**が述べられている。  
- **粒度**（table・集約）と**特徴量一覧**がある。  
- **加点／減点**・**PARTIAL 等**・**review grade**・**decision／抑制**の関係が**箇条書き以上**である。  
- **explanation** と **evidence 接続**が明記されている。  
- **001〜006／013** との境界が明確。

---

## 補足メモ（初版の外枠）

### この初版で未確定の論点

- **スコアレンジ**（0–1 vs 0–100）の最終決定。  
- **閾値**（auto／review／reject）の**初期値**と**テナント別**調整。  
- **review_point 単位スコア**の必須化の是非。  
- **LLM ベース説明**を許すか（非決定性の扱い）。  
- **`ConfidenceEvaluation` の 006 取り込み**タイミング。

### SPEC-TI-013 に引き継ぐ事項

- **005 宣言を正**としたうえでの**候補制御**と、**011 信号の補助利用**（**013 が suppression レベルの正本にならない**ことの維持）。  
- **低スコア時**の**候補タイプ制限**（どの分析候補を出さないか）。  
- **explanation** を候補カードに**どう載せるか**（007）。

### SPEC-TI-001／002／003／004／005／006 との自己点検結果

| 観点 | 結果 |
|------|------|
| 001 | **整合**。観測を変更せず warnings を特徴量化するのみ。 |
| 002 | **整合**。一次 decision を尊重しつつ再解釈を「推奨」に留めうる。 |
| 003 | **整合**。正規化を再実行しない。 |
| 004 | **整合**。メタ生成を再実行しない。 |
| 005 | **整合**。フローを実行せず、解消状態を入力とする。 |
| 006 | **整合**。新エンティティは Phase4。 |

---

## 変更履歴

### 文書の版の位置づけ

- **0.1（2026-04-08）**: 本 ID（SPEC-TI-011）の仕様書として**新規作成**した初版。  
- **0.2（2026-04-11）**: 初版の**差分追補**（特徴量の明示、「011 の出力方針」等）および体裁上の INDEX／変更履歴の整合。  
- **0.3（2026-04-19）**: **`suggestion_suppression_level` は 005 正本**、011 は確定せず信号／推奨、013 は 005 尊重＋011 補助で最終制御、境界の再掲更新。**現行 Draft**（詳細は下表）。

| 版 | 日付 | 概要 |
|----|------|------|
| 0.3 | 2026-04-19 | `suggestion_suppression_level` は 005 正本・011 は確定しない、013 は 005 尊重＋011 補助で最終制御、境界の再掲を 005／011／013 に更新。 |
| 0.2 | 2026-04-11 | 0.1 初版に対する追補（入力推奨・特徴量一覧での 003/004 フィールド名明示、出力に「011 の出力方針」、減点要因の拡充）に合わせ版上げ。変更履歴・front matter・INDEX の版／日付を本文と整合。2026-04-12〜13: 「位置づけ」の箇条書き重複を 0.2 説明へ統合、`last_updated` 更新（本文・特徴量は不変）。 |
| 0.1 | 2026-04-08 | 初版本文。責務、スコープ、用語、関連仕様、位置づけ、入出力、スコアリング原則、粒度、特徴量、加減点、review 解消、PARTIAL 等、decision／抑制、explanation、委譲、レビュー観点、成立ライン。 |
