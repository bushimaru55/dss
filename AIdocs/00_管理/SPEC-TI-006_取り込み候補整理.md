# SPEC-TI-006 取り込み候補整理

- **作成日**: 2026-04-19  
- **根拠**: [SPEC-TI-006](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md)（現行 0.1）、SPEC-TI-001〜005・011・013 の本文、[表解析仕様群_横断レビュー結果.md](表解析仕様群_横断レビュー結果.md)、[INDEX-table-intelligence.md](INDEX-table-intelligence.md)  
- **本メモの位置づけ**: **006 本文を変更しない**。**Phase4／MINOR の計画入力**として用いる。

---

## 1. 全体サマリ

- [SPEC-TI-006](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md) は **Phase 1 概念版**で、**JudgmentResult／NormalizedDataset／AnalysisMetadata／HumanReviewSession** は**必須フィールドのみ**。**002〜005・011・013 が先行定義している拡張の大半は 006 に未登録**である。  
- **最優先で Phase4 に載せるべき束**は次の 3 つである。（1）**幾何 trace**（`bbox`／セル範囲の 0-based inclusive、`trace_map`、`trace_refs` の型分離）。（2）**正規化副次メタ**（`normalization_status` 列挙と配列群）。（3）**人確認・候補・信頼度**の**下流 3 エンティティ**（`HumanReviewSession` 拡張、`ConfidenceEvaluation`、`SuggestionSet`）と **`review_points[]` 要素**。  
- **MINOR で先に足せるもの**は、**後方互換を壊さない任意フィールド**（例: `metadata_confidence_hints`、`coordinate_system` メタ）に限定するのが安全である。  
- **据え置き**は、**UI 文言**、**数式パラメータ**、**LLM プロンプト**、**閾値の初期テナント値**など**契約の外に置くべきもの**である。

---

## 2. 取り込み対象の6群一覧

| 群 | 006 現状（§5 相当） | 先行仕様の主参照 | 006 との主ギャップ |
|----|---------------------|------------------|---------------------|
| 1. JudgmentResult 拡張 | `evidence[]` は「証跡参照」とのみ | 002 | `evidence` 内部スキーマ未固定 |
| 2. NormalizedDataset 拡張 | `rows[]`, `trace_map` のみ必須 | 003 | `normalization_status`・副次配列なし |
| 3. AnalysisMetadata 拡張 | `grain`, `dimensions[]`, `measures[]` のみ必須 | 004 | `review_points`, `time_axis` 等なし |
| 4. HumanReviewSession 拡張 | `state`, `pending_questions[]` のみ | 005 | `answers[]`, 解消グレード, suppression 出力なし |
| 5. ConfidenceEvaluation | **エンティティ未独立** | 011 | `scores`, `explanation`, `decision_recommendation` |
| 6. SuggestionSet | **エンティティ未独立** | 013 | `analysis_candidates[]`, `suppression_applied[]` |

---

## 3. JudgmentResult 拡張候補

| 観点 | 内容 |
|------|------|
| **先行定義** | [SPEC-TI-002](../specs/table-intelligence/02_pipeline/SPEC-TI-002-judgment.md)（`evidence[]` の推奨フィールド、`targets` 0-based inclusive、`details`、`confidence_hint`、`refs_parse_warnings` 等） |
| **固まり度** | **006 必須 5 フィールドは固定**。**`evidence[]` 各要素の型は 002 が「推奨・暫定」**で、JSON Schema は未固定 |
| **006 に取り込むべき候補フィールド** | `evidence[].rule_id`（または同等）、`evidence[].targets[]`（範囲・セル）、`evidence[].details`（JSON 拡張）、`refs_parse_warnings` へのリンク、`confidence_hint`（任意） |
| **まだ 006 に入れない候補** | **ルール ID の全カタログ**、**002 独自の詳細キー一式の固定**（キー集合が増減しうる部分は 002 正本に残し、006 には「許容パターン」のみ） |
| **Phase4 で固定すべきもの** | **`evidence[]` の JSON Schema**、**`targets` の幾何型**（0-based inclusive の矩形・セル）、**`decision` 列挙**（006 §6 に既存）との整合 |
| **MINOR で先行追加してよいもの** | **`evidence[]` 内の任意キー許容ポリシー**（`additionalProperties` 方針の宣言のみ）、**`confidence_hint` を任意スカラーとして追加** |

---

## 4. NormalizedDataset 拡張候補

| 観点 | 内容 |
|------|------|
| **先行定義** | [SPEC-TI-003](../specs/table-intelligence/02_pipeline/SPEC-TI-003-normalization.md)（`normalization_status`: `COMPLETE`／`PARTIAL`／`FAILED`、`skipped_regions[]`、`incomplete_bindings[]`、`aggregate_rows[]`、`note_blocks[]`、`type_normalization_notes[]`、`unit_application[]` 等） |
| **固まり度** | **003 は列挙値を「006 Phase4 で固定」と明記**。**006 は `trace_map` 必須のみ** |
| **006 に取り込むべき候補フィールド** | `normalization_status`、`skipped_regions[]`、`incomplete_bindings[]`（004／005／011 への伝播に必須） |
| **まだ 006 に入れない候補** | **taxonomy 経路ごとの内部メタの全列**（まず 003 本文で安定させてから段階的に） |
| **Phase4 で固定すべきもの** | **`normalization_status` 正式 enum**、**`trace_map` の 1 対 1／1 対多の表現**、**副次配列の正式名と最小要素スキーマ** |
| **MINOR で先行追加してよいもの** | **`normalization_status` を任意文字列→後日 enum 化する場合の移行メモ**、**`aggregate_rows[]` を任意配列として追加**（要素は Phase4 で厳密化） |

---

## 5. AnalysisMetadata 拡張候補

| 観点 | 内容 |
|------|------|
| **先行定義** | [SPEC-TI-004](../specs/table-intelligence/03_analysis_human/SPEC-TI-004-analysis-metadata.md)（`time_axis`, `category_axes[]`, `filters[]`, `available_aggregations[]`, `inferred_business_meaning`, `review_required`, `review_points[]`, `metadata_confidence_hints`） |
| **固まり度** | **004 が拡張の意味正本**。**006 は必須 3＋`grain` のみ** |
| **006 に取り込むべき候補フィールド** | `review_required`（boolean）、`review_points[]`（**要素型を Phase4 で固定**）、`available_aggregations[]`（013 との契約）、`filters[]`（母集団宣言） |
| **まだ 006 に入れない候補** | **`inferred_business_meaning` の自然言語テンプレ**、**ドメイン辞書参照の詳細** |
| **Phase4 で固定すべきもの** | **`review_points[]` 要素**（`point_id`, `category`, `priority`／`severity`, `affected_fields`, `trace_refs`, `suggested_resolution_type`）、**`trace_refs` の discriminated union**（幾何／論理／ID） |
| **MINOR で先行追加してよいもの** | **`metadata_confidence_hints`（オブジェクト／文字列の緩い型）**、**`time_axis` を任意オブジェクトとして追加** |

---

## 6. HumanReviewSession 拡張候補

| 観点 | 内容 |
|------|------|
| **先行定義** | [SPEC-TI-005](../specs/table-intelligence/03_analysis_human/SPEC-TI-005-human-review-flow.md)（`state` 拡張、`pending_questions[]`、`answers[]`、`review_session_resolution_grade`、`suggestion_suppression_level` 出力、`human_resolved_uncertainty[]`、`upstream_rerun_plan` 概念） |
| **固まり度** | **006 は 4 必須のみ**。**005 が状態語彙を列挙**するが**禁止遷移は未固定** |
| **006 に取り込むべき候補フィールド** | `answers[]`（`point_id` 紐づけ）、**セッション出力としての** `review_session_resolution_grade`、`suggestion_suppression_level`（**005 正本値**）、`human_resolved_uncertainty[]` |
| **まだ 006 に入れない候補** | **画面ステップ ID**、**質問文言**、**PATCH ペイロードの HTTP 形** |
| **Phase4 で固定すべきもの** | **`state` 列挙**、**禁止遷移**、**`pending_questions[]` の要素型**（`point_id` 必須）、**011／013 へ渡すフィールド名の正式化** |
| **MINOR で先行追加してよいもの** | **`answers[]` を空配列可の任意フィールドとして追加** |

---

## 7. ConfidenceEvaluation 候補

| 観点 | 内容 |
|------|------|
| **先行定義** | [SPEC-TI-011](../specs/table-intelligence/02_pipeline/SPEC-TI-011-confidence-scoring.md)（`ConfidenceEvaluation` 仮称、`evaluation_id`, `table_id`, `scores`, `decision_recommendation`, `explanation`） |
| **固まり度** | **006 に §5.x 未掲載**。**011 が出力構造の説明正本** |
| **006 に取り込むべき候補フィールド** | `evaluation_id`, `table_id`, `scores`（複数粒度）、`decision_recommendation`, `explanation[]`（構造化要素） |
| **まだ 006 に入れない候補** | **重み・閾値の数値デフォルト**、**テナント別チューニング** |
| **Phase4 で固定すべきもの** | **新エンティティ `ConfidenceEvaluation`（名称確定）**、**`explanation` 要素スキーマ**（`factor`, `source`, `refs`）、**013 が読む集約スコアフィールド名** |
| **MINOR で先行追加してよいもの** | **`ConfidenceEvaluation` を「任意の拡張 blob」として JobRun に紐づける参照 ID のみ**（中身は Phase4） |

---

## 8. SuggestionSet 候補

| 観点 | 内容 |
|------|------|
| **先行定義** | [SPEC-TI-013](../specs/table-intelligence/03_analysis_human/SPEC-TI-013-suggestion-generation.md)（`suggestion_run_id`, `table_id`, `analysis_candidates[]`, `suppression_applied[]`, 候補の `confidence`／`readiness`／`priority`, `evidence[]`, `required_fields`／`optional_fields`） |
| **固まり度** | **006 未掲載**。**013 が構造方針と JSON 例を保持** |
| **006 に取り込むべき候補フィールド** | `suggestion_run_id`, `table_id`, `analysis_candidates[]`（**候補オブジェクトの核**）、`suppression_applied[]`（監査） |
| **まだ 006 に入れない候補** | **`presentation_hint` の UI enum 全列**、**自然言語 `title` の生成規則** |
| **Phase4 で固定すべきもの** | **候補オブジェクトの JSON Schema**、**`evidence[]` の参照規約**（`004.*`／`011.*` 文字列か URI か）、**`suppression_applied` の理由コード列挙** |
| **MINOR で先行追加してよいもの** | **`regeneration_context` を任意オブジェクトとして追加** |

---

## 9. trace / refs / evidence 系の統一候補

| 系統 | 現状の所在 | 性質 |
|------|------------|------|
| **001** | `bbox`, セル `(row,col)`, `target_range` | **幾何**・**0-based inclusive**（001 正本） |
| **002** | `evidence[].targets` | **幾何**（001 準拠） |
| **003** | `trace_map` | **幾何**（論理キー→原本セル／範囲） |
| **004** | `review_points[].trace_refs` | **幾何／論理／ID の混在しうる**（004 が座標は 001／003 と整合と明記） |
| **005** | `point_id`、004 由来 `trace_refs` | **ID**＋**間接幾何** |
| **011** | `explanation[].refs` | **ID**（`rule_id`, `point_id`, warning code） |
| **013** | 候補 `evidence[]`, `required_fields` | **論理パス**中心（例: `004.measures[]`） |

### 共通化すべきもの

- **幾何**: **単一の「CellRef／CellRange」型**（0-based inclusive、`row_min`…`col_max`）を **006 Phase4 で定義**し、001／002／003／004 の幾何参照は**それにマップ**する。  
- **ID**: **`point_id`（UUID 等）**、**`rule_id`**、**`evaluation_id`**, **`suggestion_run_id`** を **006 で ID 形式**として固定。  

### 別物として残すべきもの

- **013 の `required_fields`／`optional_fields`**: **論理パス**であり、**幾何型と同一にしない**。  
- **011 の `explanation`**: **監査・説明用**の参照集合であり、**UI ハイライト専用の座標列挙の正本にはしない**（ただし `refs` は幾何 ID に**リンクしうる**）。  

### Phase4 で最低限統一すべき項目

- **`CellRange` 型**（inclusive 規約の文字列固定）  
- **`trace_refs` の discriminated union**（`kind: geometric | logical | id` 等）  
- **`explanation.refs` と `review_points.point_id` の対応規則**  

---

## 10. 状態語彙の契約候補

| 語彙 | 所在 | 006 での扱い候補 |
|------|------|------------------|
| **002 `decision`** | `AUTO_ACCEPT`／`NEEDS_REVIEW`／`REJECT` | **006 §6 に既存** → **Phase4 で enum 正式化** |
| **003 `normalization_status`** | `COMPLETE`／`PARTIAL`／`FAILED` | **Phase4 で新 enum**（006 §6 拡張） |
| **004 `review_required`** | boolean | **MINOR または Phase4 で `AnalysisMetadata` に追加** |
| **004 `review_points`** | 配列・category 文字列 | **Phase4 で category 列挙またはパターン** |
| **005 `state`** | `OPEN`, `IN_PROGRESS`, `WAITING_RERUN`, … | **Phase4 で enum＋禁止遷移** |
| **005 `review_session_resolution_grade`** | `FULLY_RESOLVED`, … | **Phase4 で enum** |
| **005 `suggestion_suppression_level`** | `SUGGESTION_BLOCKED`, … | **Phase4 で enum**（005 正本値） |
| **011 `decision_recommendation`** | 002 と同型語彙 | **Phase4 で `decision` とは別フィールドとして固定**（マージ禁止） |
| **011 スコア帯** | 説明・閾値 | **概念**（数値レンジは 011 正本、006 には**型だけ**） |
| **013 候補 `confidence`／`readiness`／`priority`** | 候補オブジェクト | **Phase4 で候補スキーマ内に定義**（011 集約スコアと**別名**推奨は横断レビュー参照） |

### 正式 enum 候補（006 §6 拡張）

- `normalization_status`  
- `human_review_session_state`  
- `review_session_resolution_grade`  
- `suggestion_suppression_level`  
- `decision_recommendation`（002 `decision` と別立て）

### 概念のみに留めるべきもの

- **「スコア帯」ラベル**（高／中／低の**ビジネス名**）  
- **013 の `presentation_hint`**（UI 詳細は 007）

### 近接して混同しやすい語

- **`NEEDS_REVIEW`（002）** と **`review_required`（004）**  
- **`UNRESOLVED`（005）** と **`REJECT`（002）** と **`SUGGESTION_BLOCKED`（005→013）**  
- **`TI_TABLE_UNKNOWN`（taxonomy）** と **セッション未解消**

### Phase4 で固定すべき語彙

- 上記 **正式 enum 候補**＋**`decision`（既存）**  
- **`review_points[].category`**（列挙または正規表現＋正本仕様 004）

### 仕様文書内の概念のままにすべきもの

- **閾値の具体値**  
- **スコア合成係数**  
- **LLM 利用時の非決定性フラグ**

---

## 11. Phase4 / MINOR / 据え置きの分類

### Phase4 で正式契約化すべき

| 項目 | 理由 |
|------|------|
| `evidence[]`／`explanation[]` の JSON Schema | 監査・UI ハイライト・ログの**同一参照**に必要 |
| `trace_map`／幾何 `trace_refs` の型 | **再実行・差分**で座標が壊れると致命的 |
| `normalization_status`＋主要副次配列 | 004／005／011／013 の**ゲート一貫性** |
| `review_points[]` 要素型 | **005 の唯一の標準キュー入力** |
| `HumanReviewSession.state`＋禁止遷移 | **二重送信・不正遷移**防止 |
| `suggestion_suppression_level` enum | **005 正本**を API／DB で表現するため |
| `ConfidenceEvaluation` エンティティ | 011 出力の**永続化・再計算** |
| `SuggestionSet`／候補オブジェクト | 013 出力の**キャッシュ・ログ** |
| `decision_recommendation` の独立型 | 002 `decision` との**誤マージ防止** |

### MINOR で先行追加してよい

| 項目 | 理由 |
|------|------|
| `metadata_confidence_hints` | **任意**で、欠損時は 011 が推論しうる |
| `answers[]`（空可） | **後から要素厳密化**可能 |
| `coordinate_system`（001 と共有） | **読み手へのヒント**、既存必須を壊さない |
| `aggregate_rows[]`／`note_blocks[]` を任意配列 | **中身は Phase4**でよい |
| `ConfidenceEvaluation` への参照 ID のみ JobRun に追加 | **中身の Schema は後続** |

### まだ概念のまま据え置く

| 項目 | 理由 |
|------|------|
| スコア閾値・重み | **011 正本**、契約より**運用パラメータ** |
| 質問文・カード文言 | **007** |
| HTTP ステータス・エラー本文 | **014** |
| 物理カラム型・インデックス | **015** |
| `upstream_rerun_plan` の DAG 詳細 | **014** がジョブ正本 |

---

## 12. 後続仕様への影響

| 領域 | 006 取り込みによる影響 |
|------|-------------------------|
| **API（014）** | DTO＝006 型への**機械的マッピング**。**`review_points`／`SuggestionSet`／`ConfidenceEvaluation` が載ると**エンドポイント分割が明確になる。 |
| **DB（015）** | **JSON 列 vs 正規化**の判断材料。**enum は CHECK 制約**に落とせる。 |
| **UI（007）** | **契約が固定**すると、`trace_refs` から**ハイライト**、`explanation` から**ツールチップ**を**安定実装**できる。 |
| **ログ** | **JobRun** と **suggestion_run_id**／**evaluation_id** の**相関キー**が取れる。 |
| **監査** | **`evidence`／`explanation`／`suppression_applied`** の**スキーマ化**で**差分監査**が可能。 |
| **再実行** | **`trace_map`／`point_id`／`dataset_id`／`metadata_id`** の**版鎖**が 006 で明示されると **014 の idempotency** が設計しやすい。 |
| **スコア説明** | **`explanation` 構造化**で **011→007** の表示契約が固定。 |
| **候補説明** | **013 `evidence` 規約**で **004／011 への逆引き**が実装可能。 |

---

## 13. 結論と次アクション

- **結論**: **006 を Phase4 で拡張する際の中心は**（1）**trace 型の統一**、（2）**正規化・メタ・セッション・信頼度・候補の 5 ブロックの JSON Schema**、（3）**状態 enum の列挙**である。**MINOR は任意フィールドの薄い追加に限定**するのが安全である。  
- **次アクション（提案）**:  
  1. **006 の変更要求書（CR）**を本メモを添付して起票し、**Phase4 マイルストーン**に「`CellRange`＋`trace_refs` union」を**最初のマージ対象**とする。  
  2. **004／005 の `review_points` と `HumanReviewSession` を同一 PR パッケージ**で Schema 化し、**014 の mock DTO**を生成する。  
  3. **`ConfidenceEvaluation` と `SuggestionSet` の名前**を 006 で**正式確定**し、011／013 の仮称を除去する。  

---

*本メモは整理用であり、[SPEC-TI-006](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md) 本文の効力を変更しない。*
