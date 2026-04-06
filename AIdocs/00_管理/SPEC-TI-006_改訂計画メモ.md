# SPEC-TI-006 改訂計画メモ

- **作成日**: 2026-04-19  
- **根拠**: [SPEC-TI-006](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md)（現行 0.1）、[SPEC-TI-006_取り込み候補整理.md](SPEC-TI-006_取り込み候補整理.md)、[表解析仕様群_横断レビュー結果.md](表解析仕様群_横断レビュー結果.md)、SPEC-TI-001〜005・011・013、[INDEX-table-intelligence.md](INDEX-table-intelligence.md)  
- **本メモの位置づけ**: **006 本文を変更しない**。**006 の版上げ・節追加の手順書**として用いる。

---

## 1. 全体方針サマリ

- **006 は全ステージのデータ契約の単一参照源**（現行 §1）であり、**JSON Schema 完全パッケージは Phase4**（現行 §1・§10）に置く。**いきなり本文に全フィールドを列挙して密にするのではなく**、**幾何型・列挙・下流 3 エンティティの骨格**を **Step 1→3** で積み上げる。  
- **Phase4 で「契約として固定」**するのは、**trace の共通型**、**`normalization_status`／セッション state／suppression／`review_points` 要素**、**`ConfidenceEvaluation`／`SuggestionSet` の存在と必須キー**である。  
- **MINOR（006 のマイナー版）**では、**任意フィールド追加のみ**（既存必須を変えない）、**`schema_version` のルールに従い未知キーを無視できる**ことを前提にする。  
- **006 に書かないもの**は、**各パイプライン仕様の意味ルール全文**、**閾値・文言・HTTP**である。**006 には「型・列挙・参照関係」まで**とし、**意味正本は 001〜005・011・013 に残す**。

---

## 2. 現行 006 の役割再確認

| 現行節 | 役割（要約） |
|--------|----------------|
| **§1 目的とスコープ** | 単一参照源、Phase1 概念版、Phase4 で Schema |
| **§2 関係仕様** | 009／010／012／014／015 との関係 |
| **§3 用語** | artifact、`schema_version`、trace（概要） |
| **§4 入力・前提** | アップロード、`workspace_id` 任意 |
| **§5.1〜5.10** | エンティティ 10 個の**必須フィールドのみ** |
| **§6 列挙値** | `taxonomy_code` 参照、**`decision`、job status** のみドラフト |
| **§7〜10** | 例外、テスト、未確定、Phase4 で追加する章のリスト |

**ギャップ**: §5 の **`evidence[]`／`trace_map`／`state`** は**中身未定義**。§6 は **`normalization_status`・人確認・候補・信頼度**の列挙が**未掲載**。**`ConfidenceEvaluation`／`SuggestionSet` は §5 に無い**。

---

## 3. 反映対象と非対象

### 3.1 今すぐ計画に載せる（後続で 006 に反映する候補）

- **幾何参照の共通型**、`trace_map`／`trace_refs` の構造方針  
- **`normalization_status` と副次配列**（003 と同名で 006 に載せる）  
- **`review_points[]` 要素**、`HumanReviewSession` の拡張フィールド、**`suggestion_suppression_level` の enum**  
- **`ConfidenceEvaluation`／`SuggestionSet` の新 §5.x**  
- **§6 の enum 拡張**（`decision_recommendation` を `decision` と分離）

### 3.2 006 にまだ反映しない（仕様正本に残す）

- **002 のルール ID カタログ全文**、**004 の分析アルゴリズム**、**011 の数式・閾値**  
- **007 の文言**、**014 のパス設計**、**015 の正規化方針**  
- **`upstream_rerun_plan` の DAG 詳細**

### 3.3 Phase4 で固定するもの

- **共通 JSON Schema パッケージ**（現行 §10 にある宣言の具体化）  
- **`evidence[]`／`explanation[]`／`review_points[].trace_refs` の discriminated union**  
- **禁止遷移付き `HumanReviewSession.state`**

### 3.4 MINOR で先行追加できるもの

- **`coordinate_system`（TableReadArtifact または TableCandidate 側の任意メタ）**  
- **`metadata_confidence_hints`、`answers[]`（空可）**  
- **`aggregate_rows[]` を配列型のみ先行**（要素は TBD）

### 3.5 既存 006 と衝突しうる箇所

- **`decision`（002）と `decision_recommendation`（011）**を**同一列挙にマージ**すると**横断レビューで指摘の通り事故る**  
- **`bbox` の inclusive 規約**が §5.3 に**明示なく**、001 の正本のみ参照だと**読者が 006 単体で誤読**しうる  
- **`JobRun.kind` に `SUGGEST` 等がある**が **`SuggestionSet` エンティティが §5 に無い**（参照先が宙に浮く）

### 3.6 backward compatibility の考え方

- **必須フィールドの追加・意味変更は MAJOR**（`schema_version` 更新）。  
- **任意フィールドの追加は MINOR**。**読み手は未知キーを無視**（現行 §8 の方針を §1 または §10 に**明文化してから**運用する）。  
- **列挙値の拡張**は、**既存値の意味を変えない**限り **MINOR**。**値の意味変更は MAJOR**。

---

## 4. 追加・改訂候補の章節マッピング

| 改訂候補 | 反映先（006 現行） | 新設 vs 拡張 | 依存 | 反映順序（計画） |
|----------|-------------------|--------------|------|------------------|
| **幾何・trace 共通型** | **新設 §5.0 または §3.1「参照型」**、§5.3〜5.7 で参照 | **新設＋既存の説明列拡張** | 001／003／004 | **Step 1** |
| **JudgmentResult 拡張** | **§5.6** 表に列追加＋**§6** は `decision` 維持 | 拡張 | 幾何型、002 | Step 1〜2 |
| **NormalizedDataset 拡張** | **§5.7** | 拡張 | 幾何型、003、§6 enum | Step 1〜2 |
| **AnalysisMetadata 拡張** | **§5.8** | 拡張 | `review_points` 型、004 | Step 2 |
| **HumanReviewSession 拡張** | **§5.9** | 拡張 | §6 state／grade／suppression、005 | Step 2 |
| **ConfidenceEvaluation** | **新設 §5.11**（5.10 JobRun の後） | 新設 | §6 `decision_recommendation`、011 | Step 2 |
| **SuggestionSet** | **新設 §5.12** | 新設 | §5.11（参照）、013、§5.10 | Step 2〜3 |
| **trace／refs／evidence 統一説明** | **§3 用語**＋**§10**（Schema 章）に「参照規約」小節 | 新設小節 | 全 §5 | Step 1 から継続 |
| **状態語彙 enum** | **§6** に小節追加 | 拡張 | 005／003／011 | Step 1〜2 |

**JobRun（§5.10）**: **任意で** `evaluation_ref`／`suggestion_run_ref` を MINOR で足すのは **Step 2 以降**（014 と整合後）。

---

## 5. trace 系統一の最小実装方針

| 種別 | 正式型候補（006 に載せる名前例） | 内容 |
|------|----------------------------------|------|
| **幾何** | `CellRef`（`row`, `col`）、`CellRangeInclusive`（`row_min`…`col_max`） | **0-based inclusive** を型説明に**固定文で記載** |
| **論理** | `LogicalFieldPath`（文字列規約）または `dimension_id`／`measure_id` | **004／013 の `affected_fields`／`required_fields` と同一規約へ寄せる** |
| **ID** | `PointId`, `RuleId`, `WarningCode`, `EvaluationId`, `SuggestionRunId` | **文字列形式（UUID 等）は §9／§10 で固定** |

**discriminated union**: **`TraceRef`** を `oneOf: { geometric, logical, id }` とする案を **Phase4 の最小実装**とする。**004 `trace_refs`／002 `targets`／011 `refs`** は**この union にマップ**する旨を §3 または §5 の「参照規約」に書く。

**Phase4 の最小実装**: **`CellRangeInclusive`＋`PointId`＋`TraceRef` union の 3 点セット**を先に Schema 化する。**`trace_map` の内部キー構造**は **003 と同一ドキュメントで確定**した行を 006 に貼る（**コピーではなく参照 ID**でよい）。

**後回し**: **結合セル内部の従属座標の正規化**、**複数シート跨ぎ参照**、**013 `evidence` を URI にするか文字列パスにするか**の最終決定（**014 固定後**）。

---

## 6. 状態語彙の正式契約候補

| 語彙 | 006 で正式 enum 化 | 006 では概念のみ | 別仕様正本のまま |
|------|-------------------|------------------|------------------|
| **002 `decision`** | ✓（§6 既存を Phase4 で厳密化） | — | 002 が意味・ルール |
| **003 `normalization_status`** | ✓（§6 新設） | — | 003 がいつ PARTIAL にするか |
| **004 `review_required`** | ✓（boolean は §5.8、**必須化は Step 2 で検討**） | — | 004 が真偽の根拠 |
| **`review_points[].category`** | ✓（§6 に列挙またはパターン） | — | 004 がカテゴリ語彙の正本 |
| **005 `HumanReviewSession.state`** | ✓ | — | 005 が遷移ルール |
| **`review_session_resolution_grade`** | ✓ | — | 005 |
| **`suggestion_suppression_level`** | ✓ | — | 005 |
| **011 `decision_recommendation`** | ✓（**`decision` と別 enum として §6 に並記**） | — | 011 が閾値ロジック |
| **013 候補 `confidence`／`readiness`／`priority`** | **型（number 等）と意味行のみ §5.12** | **閾値・合成式は載せない** | 013 |

**命名衝突**: **候補オブジェクトの `confidence` と 011 の表単位スコア** → **006 では `candidate_confidence` 等へのリネームを Step 2 で検討**（[表解析仕様群_横断レビュー結果.md](表解析仕様群_横断レビュー結果.md) の「次版で修正」に整合）。

**最低限統一**: **`decision` ≠ `decision_recommendation`**、**`NEEDS_REVIEW` ≠ `review_required` の同義扱い禁止**、**`SUGGESTION_BLOCKED` ≠ `REJECT`** を §3 用語または §7 に**一文で固定**。

---

## 7. Step 1 / Step 2 / Step 3 の反映順序

### Step 1: 先に最小限固定するもの

| 対象 | 理由 | 完了条件 |
|------|------|----------|
| **幾何型 `CellRef`／`CellRangeInclusive`＋0-based inclusive 宣言** | 001〜004 が**既に同一規約**で動いており、**後から変えるコストが最大** | §3 または新設「参照型」に**型定義と inclusive の一文**がある |
| **`TraceRef` union の設計方針（本文レベル）** | 横断レビューで**三層混在**がリスクと確定済み | §3 または §10 草案に**種別列挙**がある |
| **§6 に `normalization_status` enum 草案** | 003／004／011 が**既に値名を使用** | §6 に**3 値＋説明**が載る |
| **`decision` と `decision_recommendation` の分離宣言** | 011／002 の**複線が明示済み** | §6 に**別小節**がある |

### Step 2: その次に反映するもの

| 対象 | 理由 | 完了条件 |
|------|------|----------|
| **§5.6 `evidence[]` スキーマ（Phase4 Schema パッケージの第1版）** | 002 が**構造推奨済み** | JSON Schema ファイルがリポジトリにあり、§10 が**パスを指す** |
| **§5.7 `normalization_status`＋`skipped_regions`／`incomplete_bindings` 必須化の是非確定** | 004／005 への伝播の要 | §5.7 表に**行が追加**され、**必須／任意が明示** |
| **§5.8 `review_points[]` 要素型＋`review_required`** | **005 の標準入力**が固定される | §5.8 に**要素フィールド表**がある |
| **§5.9 `state` enum＋`answers[]`＋grade／suppression** | 011／013 の**入力が閉じる** | §5.9 表更新、§6 に**state／grade／suppression** |
| **新設 §5.11 `ConfidenceEvaluation`** | 011 出力の**永続化単位** | 必須フィールド表が§5.11にある |

### Step 3: 後続仕様や API／DB を見ながら反映するもの

| 対象 | 理由 | 完了条件 |
|------|------|----------|
| **新設 §5.12 `SuggestionSet`＋候補オブジェクト完全スキーマ** | **013 の `evidence` 規約**が 014 の**シリアライズ形**に依存 | OpenAPI／DB 草案と**突合済み** |
| **§5.10 JobRun への外部参照フィールド** | **ジョブと成果物の結び**は 014 正本 | 014 の **DTO 表**と 006 が**1:1** |
| **§10 の「014 エンドポイント対応表」「015 カラム対応表」** | 現行 §10 が**宣言のみ** | 表が**埋まる** |
| **監査ログフィールド一覧（§10）** | **explanation／suppression_applied** の保存方針は運用依存 | 012／015 と**整合したリスト** |

---

## 8. backward compatibility の考え方

- **読み手**: 未知フィールド無視（** tolerant reader**）。**書き手**: **既存必須を欠かさない**（**strict writer**）。  
- **MINOR 追加**: **任意キーのみ**。**必須キー追加**は **Step 2 以降で「バージョン協調日」を決めて**実施。  
- **enum 拡張**: **新値追加は MINOR**（旧クライアントは未知値を「その他」扱いにできるよう、**014 で文字列保持**も検討）。**既存値の意味変更は禁止**（MAJOR）。  
- **`schema_version`（File 等）**と **006 文書版**の対応表を **§1 または §10** に**1 表で**置く（**Step 2**）。

---

## 9. リスクと回避策

| リスク | 回避策 |
|--------|--------|
| **既存 006 と矛盾** | **必須 5 項目は変えず**、まず**§3・§6・新設型**から入れる。**表の「必須」列は差分 PR でレビュー** |
| **責務が 006 に吸い込まれすぎる** | 各 §5.x の説明列に**「意味正本は SPEC-TI-xxx」**を**必ず残す**。**アルゴリズムは書かない** |
| **Phase4 前に Schema を固めすぎる** | **Step 1 は「方針＋幾何型＋列挙草案」まで**。**完全 Schema は Step 2 から** |
| **API／DB 未整備で型だけ先行** | **JobRun 参照 ID は Step 3**。**Step 1〜2 はパイプライン内部 JSON のみ**で完結させるか、**feature flag** で公開範囲を限定 |
| **trace 統一が中途半端** | **Phase4 最小セット（§5）を完了定義**に含める。**`TraceRef` 未対応のフィールドは明示リスト**に残し、**次 MAJOR で削除** |

---

## 10. 結論と次アクション

- **結論**: **006 改訂は「型と列挙の骨格 → エンティティ拡張 → 014／015 同期」**の順が**取り込み候補整理・横断レビューと整合**する。  
- **次アクション**:  
  1. **本メモを承認**し、**006 の 0.2 または「Phase4 作業ブランチ」**のスコープを **Step 1 のみ**に切る。  
  2. **JSON Schema リポジトリ配置**（現行 §10）の**パス規約**を先に決め、**CellRange の 1 ファイル**からコミットする。  
  3. **004／005 と同一 PR ライン**で **`review_points` 要素**のフィールド名を**凍結**する（**006 §5.8 と 004 の表を diff 合わせ**）。  

---

*本メモは計画用であり、[SPEC-TI-006](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md) 本文の効力を変更しない。*
