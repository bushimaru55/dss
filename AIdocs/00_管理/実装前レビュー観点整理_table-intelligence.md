---
title: 実装前レビュー観点整理_table-intelligence
status: Draft
version: 0.1
last_updated: 2026-04-07
---

## 1. 文書情報

| 項目 | 値 |
|------|-----|
| 文書名 | 実装前レビュー観点整理（表インテリジェンス） |
| 版 | 0.1 |
| 状態 | Draft |
| 最終更新 | 2026-04-07 |
| 位置づけ | **実装着手前のレビュー会アジェンダ兼チェックリスト**（正本仕様ではない） |

---

## 2. 目的

- **006 / 014 / 015**、**OpenAPI 叩き台**、**DDL 叩き台**、**API × DTO × DB 対応表**を前提に、実装前に **論点・受け入れ条件・危険箇所**を整理する。
- **実装者・レビュアー・仕様側**が同じ観点で確認できるようにし、**後戻りの大きい順**にレビュー順序を示す。
- 問題の**断定**ではなく、**確認ポイント**と**受け入れの目安**を並べる。

---

## 3. レビュー対象

| 種別 | パス | 備考 |
|------|------|------|
| DTO / データ契約（正本） | [SPEC-TI-006-io-data.md](../specs/table-intelligence/01_foundation/SPEC-TI-006-io-data.md) | フィールド・列挙の正本 |
| API 契約（正本） | [SPEC-TI-014-api.md](../specs/table-intelligence/04_system/SPEC-TI-014-api.md) | 論理リソース・識別子・実行/参照の正本 |
| DB 設計（正本） | [SPEC-TI-015-db-design.md](../specs/table-intelligence/04_system/SPEC-TI-015-db-design.md) | 永続化・世代・テーブル粒度の正本 |
| エラー（正本） | [SPEC-TI-012-errors.md](../specs/table-intelligence/01_foundation/SPEC-TI-012-errors.md) | `error_code` 体系 |
| OpenAPI 叩き台 | [table-intelligence-openapi-draft.yaml](../specs/table-intelligence/04_system/openapi/table-intelligence-openapi-draft.yaml) | 機械可読叩き台（014/006 ベース） |
| DDL 叩き台 | [table-intelligence-ddl-draft.sql](../specs/table-intelligence/04_system/sql/table-intelligence-ddl-draft.sql) | 015 の SQL 叩き台 |
| 横断対応表 | [API_DTO_DB対応表_table-intelligence.md](API_DTO_DB対応表_table-intelligence.md) | 接続面の一覧 |

**関連正本（ドメイン）**: 001 観測、002 `decision`、003 `dataset_id`、004 `metadata_id` / `review_points`、005 suppression / `HumanReviewSession`、011 `decision_recommendation`、013 suggestion。

---

## 4. レビュー観点サマリ

### 4.1 レビュー順序（推奨）

| 順 | 観点 | 理由 |
|----|------|------|
| 1 | **識別子・レイヤ差**（`evaluation_ref` ⇔ `evaluation_id` 等） | 全レイヤに横断し、誤るとデータが一貫しなくなる |
| 2 | **`decision` / `decision_recommendation` の分離** | API・OpenAPI・DDL・UI で混同しやすい |
| 3 | **005 suppression と DB/API の役割** | 正本と投影の取り違えで監査・候補説明が破綻 |
| 4 | **review session：状態遷移 vs HTTP（PATCH 有無）** | OpenAPI ギャップと実装方針の確定が必要 |
| 5 | **stale / rerun / latest の truth** | 409、世代、`artifact_relation` の運用合意 |
| 6 | **suggestion の主入力 `metadata_id`** | 013/014/015 の接続の芯 |
| 7 | **テナント・RLS・認可** | 後付けで難易度が跳ねる |
| 8 | **enum / CHECK / idempotency** | 実装しながら詰められるが、境界の合意は早いとよい |

### 4.2 優先度が高いもの（後戻りコスト大）

- **ID / ref の橋渡し**（対応表 §6 と一致しているか）。
- **truth ソース**（`is_latest` のみか、supersede 鎖か、一覧 API の既定は何か）。
- **review の state 更新**を **どの HTTP 操作で表すか**（014 と OpenAPI のギャップ解消）。
- **`/tables/{table_id}/artifacts` の集約責務**（アプリ・ビュー・複数クエリの分担）。

### 4.3 観点一覧表（クイック参照）

| # | 領域 | 主な正本 | 叩き台での典型リスク |
|---|------|----------|------------------------|
| 1 | API 契約 | 014 | path/method 不足、実行/参照の混同、409 条件の未定 |
| 2 | DTO / schema | 006 | enum 未固定、summary vs full、フィールド欠落 |
| 3 | DB / DDL | 015 | CHECK 暫定、多型 FK なし、RLS 未着手 |
| 4 | 横断対応 | 対応表 | 名前のレイヤ差の漏れ、集約責務の曖昧さ |
| 5 | 運用 | 014/015/012 | 認証・冪等・監査・観測性の未記載 |

---

## 5. 詳細レビュー観点

### 5.1 API 契約観点（正本：**014**、補助：**OpenAPI**）

| 確認すること | 正本 | 受け入れの目安 | 典型的なズレ |
|--------------|------|----------------|--------------|
| path / method が論理リソースを覆うか | 014 §8〜11 | 対応表に列挙された操作が **意図的に除外されていない** | 014 に **PATCH review-session**（§10）があるが **OpenAPI に `patch` 無し** |
| 実行系と参照系の分離 | 014 §4.2 | POST は `job_id` / ref、GET は実体 | 同期で巨大ボディを返しすぎる |
| rerun（ジョブ・review 後） | 014 §8, §12 | 新 `job_id` / 新 artifact 行の説明と整合 | 段階指定ペイロードが **014 次版** |
| stale / conflict | 014 §12〜13 | 409 / 012 コードの対応が **文書または OpenAPI どちらかで追跡可能** | HTTP と `error_code` の表が **未固定** |
| response code / `error_code` 粒度 | 012, 014 §13 | レビュー会で「表を誰が作るか」決まっている | OpenAPI `default` のみで 012 未接続 |
| PATCH vs 専用サブリソース | 014 §10 | どちらかに寄せた方針が **1 行で共有されている** | 仕様に PATCH 記載、OpenAPI に無い |

### 5.2 DTO / schema 観点（正本：**006**、補助：**OpenAPI components**）

| 確認すること | 正本 | 受け入れの目安 | 典型的なズレ |
|--------------|------|----------------|--------------|
| request/response フィールドが 006 と矛盾しないか | 006 §5〜 | 対応表と OpenAPI schema 名が追跡可能 | 叩き台で `object` + `additionalProperties` のみ |
| enum の固定箇所 | 006 §6 | **未固定リスト**がレビュー記録に残る | DDL の CHECK と 006 の差 |
| summary と full | 014, OpenAPI | 一覧・ジョブ応答が **過剰に full** になっていないか | `JobSummary` vs `JobDetail` の境界 |
| `decision` と `decision_recommendation` | 002 vs 011 | **別フィールド・別 DTO パス** | 同一レスポンスに両方あり、ラベル誤り |

### 5.3 DB / DDL 観点（正本：**015**、補助：**DDL 叩き台**）

| 確認すること | 正本 | 受け入れの目安 | 典型的なズレ |
|--------------|------|----------------|--------------|
| PK / FK が 015 §8 の主要リレーションを満たすか | 015 §7〜8 | `metadata_id`→`dataset_id`、`session_id`→`metadata_id` 等 | `artifact_relation` 多型で FK なし（DDL TODO） |
| 世代 | 015 §10 | `artifact_version` / `superseded_by` / `is_latest` の運用ルールが一言で共有 | アプリだけの latest 解決 |
| `suppression_record` | 015 付録 A | 005 正本を **行で保持**する方針と一致 | session JSON のみに偏る |
| `workspace_id` | 015 §6, §13 | どのテーブルに必須か合意 | RLS 前にテナント漏れ |
| CHECK / UNIQUE / idempotency | 015, DDL TODO | `(workspace_id, idempotency_key)` 等の **タイミング**が決まる | 早期 UNIQUE 失敗 vs 後回し |
| RLS / 論理削除 / 監査 | 015 §13, §7.15 | `audit_log` との相関 ID 方針 | 実装後半に押し込み |

### 5.4 API × DTO × DB 接続観点（正本：**対応表**＋ **014 §5 / 015 §5.2**）

| 確認すること | 正本 | 受け入れの目安 |
|--------------|------|----------------|
| `evaluation_ref` ⇔ `evaluation_id` | 014 §5.1.1, 015 §5.2 | API/JSON と DB 列名の対応が **実装メモに1ページ**ある |
| `suggestion_run_ref` ⇔ `suggestion_run_id` | 同上 | 同上 |
| `job_id` / `table_id` / `dataset_id` / `metadata_id` / `session_id` | 006, 015 §6 | 対応表 §5〜6 と実装の参照経路が一致 |
| `/artifacts` 集約 | 014 §9, 015 §7.14 | **集約はアプリ層 or ビュー**のどちらかに決めた |
| `review_points` の取得元 | 004, 対応表 | `GET .../review-points` は **metadata 行の投影**でよいか明確 |
| suggestion の主入力 | 013, 014 §11 | `metadata_id` 必須、`dataset_id` は補助 |

### 5.5 実装・運用観点（正本：**014 §14**、**015 §13**、**012**）

| 確認すること | 正本 | 受け入れの目安 |
|--------------|------|----------------|
| 認証 / 認可 | 014 §14 | ロール（読取/実行/人確認）と **API 操作のマッピング草案** |
| テナント境界 | 015, 014 §14.3 | 404 マスク等の **方針レベル**で共有 |
| 冪等性 | 014 §4.5, 7.1 | `Idempotency-Key`、answers の二重送信の **担当層**（API vs DB） |
| 再実行時の世代 | 015 §10 | 新行 + supersede の **テスト観点**が書ける |
| stale data | 014 §12.4 | 409 の **再現手順**がレビューで言える |
| 監査ログ | 015 §7.15, 014 §14.2 | `job_id` / `session_id` / request id の **ログ項目**が列挙できる |
| 観測性 | （実装標準） | メトリクス・トレースの **最低限のキー**（`job_id` 等） |
| 将来の正規化 | 015 §16 | `review_point` テーブル化などは **後続**と割り切る |

---

## 6. 重点確認事項（危険度が高い項目）

| ID | 項目 | なぜ危険か | 確認時の参照 |
|----|------|------------|--------------|
| P1 | **`decision` / `decision_recommendation` の混同** | 002 と 011 の責務が崩れ、製品説明・監査が誤る | 006, 014 §5.4, 015 §7.5/7.10, OpenAPI schema 名 |
| P2 | **suppression の正本（005）と投影** | 候補・API が「正本」に見えてしまう | 005, 015 付録 A, `suppression_record` vs `suggestion_set.suppression_applied` |
| P3 | **review session state と PATCH ギャップ** | 実装が 014 と OpenAPI のどちらを見るかブレる | 014 §10, OpenAPI（`patch` 無し）, 005 状態機械 |
| P4 | **stale / rerun / latest の truth** | 409 と DB の `is_latest` が矛盾 | 014 §12, 015 §10, `artifact_relation` |
| P5 | **idempotency** | 二重ジョブ・二重回答の事故 | 014 §4.5, DDL UNIQUE TODO |
| P6 | **RLS / `workspace_id`** | 他テナント参照 | 015 §13, DDL TODO |
| P7 | **enum 未固定** | 実行時バリデーションがブレる | 006 §6, DDL CHECK |
| P8 | **`/artifacts` 集約責務** | N+1、パフォーマンス、仕様外の「隠れ結合」 | 対応表, 014 §9 |

---

## 7. 実装着手前の受け入れ条件

### 7.1 実装前に fix 必須（合意がないと着手が危険）

- **識別子の橋渡し**（`evaluation_ref` / `suggestion_run_ref` と DB 列名）を **チームで言語化**したこと（対応表で足りなければ1枚補足）。
- **`decision` と `decision_recommendation` を混ぜない**こと（API ドキュメント・コードレビュー基準）。
- **005 の suppression 正本**と **`suppression_record` / 投影**の役割分担の合意。
- **review session の state 更新**を **どの API で表すか**（PATCH 追加 vs 専用操作 vs 014 改訂）の **方針決定**。
- **stale reference（409）**の **最低限の発生条件**（例：旧 `metadata_id` で suggestion）の合意。

### 7.2 実装しながら詰めてよい（ただし追跡チケット必須）

- **HTTP ステータス ↔ 012 `error_code` の完全対応表**（OpenAPI 化と同時でも可）。
- **DDL の CHECK** 値と **006 enum** の完全一致。
- **`(workspace_id, idempotency_key)` 部分一意**の時間窓・NULL 扱い。
- **`summary` vs `full` の境界**（フィールド選択・ページネーション）。
- **`/artifacts` の実装方式**（ビュー vs アプリ集約）。

### 7.3 後続フェーズへ送ってよい

- **`suggestion_candidate` サテライト化**（015 §7.12）。
- **review_point 正規化テーブル**（015 §16）。
- **パーティション・読み取りレプリカ**（015 §16）。
- **JSON Schema の完全パッケージ**（006 Phase 4）。

---

## 8. 今回は未 fix でもよい事項（過剰な足止め防止）

- OpenAPI / DDL の **TODO コメント**に書いてある **細部の最適化**（部分 index、トリガ）。
- **Webhook / SSE** など 014 §16 の将来拡張。
- **大容量 artifact のオブジェクトストレージキー**への切替（015 §7.4 で許容される実装選択）。
- **全エンドポイントの response 例の網羅**（叩き台の段階では省略可）。

---

## 9. 次アクション

| アクション | 担当イメージ | 出力 |
|------------|--------------|------|
| **実装前レビュー会** | 全員 | §6 重点 P1〜P8 を **アジェンダ化**し、§7.1 を **合意記録**（議事録） |
| **OpenAPI 修正** | API | `PATCH` または **意図的に無い**旨の注記、012 対応表の置き場 |
| **DDL 修正** | DB | RLS / UNIQUE の **マイグレーション順**、enum 確定後の CHECK |
| **仕様へ戻す論点** | 仕様 | **014**：PATCH の最終形、HTTP と 012 の対応。**006**：enum 確定のタイムボックス |
| **対応表メンテ** | 仕様 or 実装 | 合意が変わったら **対応表の版上げ** |

---

## 付録 A. 重点項目まとめ（レビュー会で読み上げ用）

1. **ID/ref**：API 名と DB 列名の差は **値同一**で統一する（015 §5.2）。
2. **decision**：002 / `judgment_result` のみ。**recommendation** は 011 / `confidence_evaluation` のみ。
3. **suppression**：005 正本。**DB は `suppression_record`**。suggestion は投影。
4. **review**：state は **005 正本**。HTTP は **PATCH 有無を OpenAPI と揃える**。
5. **suggestion**：**`metadata_id` 主入力**。013 は 004 主、011/005 は読む。
6. **stale**：**409** と **世代**（`is_latest` / `artifact_relation`）をセットで設計する。
7. **テナント**：**RLS** は「後で」と言わず、**§7.1 で方針だけでも**決める。

---

## 付録 B. 実務向け短いまとめ

- まず **対応表 + 014 §5 + 015 §5.2** で ID を揃える。
- 次に **005 と review の HTTP**（PATCH ギャップ）を決める。
- 並行して **409 と世代**のテストケースを **1本**書く。
- **RLS** は「後回し」ではなく **スコープとタイミング**を決めてから実装に入る。

---

## 変更履歴

| 版 | 日付 | 概要 |
|----|------|------|
| 0.1 | 2026-04-07 | 初版。実装前レビュー観点・受け入れ条件・重点項目。 |
