# Table Intelligence API — 利用者向けエラー・HTTP ステータス一覧

**対象**: `table_intelligence` が提供する **`/api/v1/`** 配下の API を呼び出す人（アプリ実装者・連携担当）。  
**正本との関係**: 振る舞いの詳細は [SPEC-TI-014-api.md](./SPEC-TI-014-api.md)、機械可読な契約は [OpenAPI 叩き台](./openapi/table-intelligence-openapi-draft.yaml)（`document_version` 表記の版）を優先してください。本文の「**今の実装**」は **MVP の Django 実装**に合わせています。

---

## 1. まず読む（共通ルール）

### 1.1 成功したときの体

- 操作ごとに **200 / 201 / 202** などが返ります（後述の表の「成功」列）。
- 本文は JSON です。ジョブ系では **新規受理が 202**、**同じ冪等キーでの再送が 200** になることがあります（ジョブ開始 API）。

### 1.2 失敗したときの体（`/api/v1/*`）

エラー時、本文は次の形になることを **前提にしてよい**です（[P4-1 / SPEC-TI-014 §16.4](./SPEC-TI-014-api.md)）。

| フィールド | 意味 |
|------------|------|
| `error_code` | 機械可読な種別（例: 未認証、見つからない、入力不備）。 |
| `detail` | 人が読む説明（短文）。 |
| `errors` | ある場合のみ。フィールド単位の検証メッセージ（主に **400**）。 |

代表的な `error_code`（ステータスとの対応は実装のマッピングに従います）:

| HTTP | `error_code`（代表例） |
|------|-------------------------|
| 400 | `TI_VALIDATION_ERROR` / `TI_BAD_REQUEST` |
| 401 | `TI_AUTHENTICATION_REQUIRED` |
| 403 | `TI_PERMISSION_DENIED`（**MVP ではあまり使わない**。多くは 401） |
| 404 | `TI_NOT_FOUND` |
| 409 | `TI_CONFLICT`（**現状ほとんど返しません** — 下記「将来枠」） |
| その他 | `TI_ERROR` など |

### 1.3 認証（401）

- **配線済みの MVP 実装**（`backend/table_intelligence/urls.py` に載る path）では **すべて認証必須**（DRF `IsAuthenticated`）。トークンが無い・無効な場合は **401** です。
- OpenAPI **`0.1.7-draft` 以降**では、ドキュメントに載る **すべての operation** に **`401 Unauthorized`** を path 上で列挙しています（生成クライアントと本ガイドの表記を一致させるため）。

### 1.4 404 と「404 マスク」（越境）

次のどちらでも、クライアントから見ると **同じ 404** になることがあります（[SPEC-TI-014 §14.3](./SPEC-TI-014-api.md)）。

1. **本当に存在しない** ID（存在しないジョブ・メタデータなど）。
2. **別テナント（workspace）に属するデータ**を、権限のないトークンで読もうとした場合。

**意図**: 他社のデータの有無を推測されにくくするためです。**404 だけでは「存在しない」のか「越境」のか区別できません**。正しい `workspace_id` とトークンで再取得してください。

### 1.5 400 と 404 の使い分け（覚え方）

- **400**: 「送り方がおかしい」「この workspace 内ではその組合せは許されない」（例: suggestion で `metadata_id` に対して `dataset_id` が食い違う）。
- **404**: 「その ID は見つからない **または** 越境のため見せない」。
- **409**（将来）: 「データはあるが、**今のサーバの状態ではその操作は受け付けない**。再取得や別操作で直せる可能性がある」（[§13.1 マトリクス](./SPEC-TI-014-api.md)）。

### 1.6 403 について

- OpenAPI には **共通部品として 403** の定義がありますが、**MVP では path ごとにはほとんど列挙していません**。
- 未認証は **401** が中心です。**403** は、今後「ログインはしているがこの操作は禁止」などを明示するときの余地です。

### 1.7 409（競合）— 今の実装と将来

- **今の実装**: **`POST /suggestion-runs`** だけ、**superseded な `metadata_id`** のとき **409**（`TI_CONFLICT`）。判定は **`artifact_relation`**（job / review の rerun 後 materialize で記録される metadata 旧→新 edge）。その他の path の 409 は **主に将来枠**（§13.1）。
- **OpenAPI**: **0.1.8** で上記と一致。詳細は [SPEC-TI-014 §13.1](./SPEC-TI-014-api.md)。

### 1.8 `default` / 500 系

- OpenAPI 上の **default** は「上記以外のエラー」用です。サーバ内部エラーなどで **5xx** になる場合もあります。本文は引き続き `error_code` + `detail` 形式になることを目指しますが、クライアントは **再試行・サポート連絡**も考慮してください。

---

## 2. 操作別一覧（主要 API）

表の見方:

- **成功**: 代表的な成功時の HTTP ステータス。
- **400 / 401 / 404 / 409**: その操作で **想定される**意味。**409 は将来枠**の列で補足。
- **備考**: 404 マスク、実装メモ。

パスは OpenAPI のサーバ URL からの **相対パス**です（例: `/table-analysis/jobs`）。

### 2.1 Jobs（ジョブ）

| 操作 | メソッド・パス | 成功 | 400 | 401 | 404 | 409（将来枠） | 備考 |
|------|----------------|------|-----|-----|-----|----------------|------|
| ジョブ開始 | `POST /table-analysis/jobs` | **202** 新規 / **200** 冪等再送 | 入力不正 | 未認証 | 無効な `workspace_id` 等 **マスク** | なし（OpenAPI 上もなし） | 冪等は `Idempotency-Key` ヘッダ。 |
| ジョブ参照 | `GET /table-analysis/jobs/{job_id}` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | |
| ジョブ rerun | `POST /table-analysis/jobs/{job_id}/rerun` | **201** | ボディ不正 | 未認証 | 不存在・**越境マスク** | 将来ありうる（lineage・進行中など）— **MVP 未実装** | OpenAPI には 409 なし。 |

### 2.2 成果物参照（datasets / metadata / evaluations）

| 操作 | メソッド・パス | 成功 | 400 | 401 | 404 | 409 | 備考 |
|------|----------------|------|-----|-----|-----|-----|------|
| 正規化データセット | `GET /datasets/{dataset_id}` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | MVP 形は `TiMvpNormalizedDataset`。 |
| 分析メタデータ | `GET /metadata/{metadata_id}` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | |
| review_points | `GET /metadata/{metadata_id}/review-points` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | 現行 MVP の `urls.py` には **未配線**（OpenAPI は配線後の契約用）。 |
| 信頼度評価 | `GET /evaluations/{evaluation_ref}` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | `evaluation_ref` は DB の evaluation ID と同じ値。 |

### 2.3 Review sessions（人確認）

| 操作 | メソッド・パス | 成功 | 400 | 401 | 404 | 409（将来枠） | 備考 |
|------|----------------|------|-----|-----|-----|----------------|------|
| session 作成 | `POST /review-sessions` | **201** | 入力不正 | 未認証 | 参照 `metadata_id` が無い・**越境マスク** | なし | |
| session 取得 | `GET /review-sessions/{session_id}` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | |
| answers 投稿 | `POST /review-sessions/{session_id}/answers` | **200** | 入力不正 | 未認証 | 不存在・**越境マスク** | **禁止遷移・楽観ロック等** — **MVP 未実装** | リクエスト形は `TiMvpSubmitReviewAnswersRequest`（014 / OpenAPI）。 |
| review 後 rerun | `POST /review-sessions/{session_id}/rerun` | **202** | — | 未認証 | 不存在・**越境マスク** | **二重起動・状態不適格等** — **MVP 未実装** | |
| suppression 参照 | `GET /review-sessions/{session_id}/suppression` | **200**（配列） | — | 未認証 | 不存在・**越境マスク** | なし | レコードが無いときは **空配列 `[]`**。 |

### 2.4 Suggestion runs（候補生成）

| 操作 | メソッド・パス | 成功 | 400 | 401 | 404 | 409（将来枠） | 備考 |
|------|----------------|------|-----|-----|-----|----------------|------|
| run 開始 | `POST /suggestion-runs` | **202** | 参照不整合（dataset / evaluation / session と metadata） | 未認証 | `metadata_id` 無効・**越境マスク** | **superseded metadata**（`artifact_relation` に旧→新 metadata の SUPERSEDES あり）→ **409** + `TI_CONFLICT` | 400 は同一 workspace 内の参照の組合せ誤り。409 は **より新しい metadata_id** へ切替。 |
| SuggestionSet 取得 | `GET /suggestion-runs/{ref}` | **200** | — | 未認証 | 不存在・**越境マスク** | なし | |
| 候補一覧 | `GET /suggestion-runs/{ref}/candidates` | **200** | — | 未認証 | 不存在・**越境マスク** | **付けない**（読取は 200/404 のみ。stale は POST 側） | §13.1 / OpenAPI 0.1.6 整合。 |

### 2.5 参考: Tables（表・判定・成果物一覧）

**GET** 中心。**401**（未認証）・**404**（不存在・越境マスク）は他節と同じ解釈です。  
**現行 MVP の `table_intelligence` `urls.py` にはこれらの path は未配線**です。OpenAPI は **将来配線時も `IsAuthenticated` 前提**で **401 を列挙**済み（`0.1.7-draft`）。

| パス（いずれも GET） | 成功 | 備考 |
|----------------------|------|------|
| `/tables/{table_id}` | 200 | サマリ |
| `/tables/{table_id}/read-artifact` | 200 | 読取成果 |
| `/tables/{table_id}/decision` | 200 | 判定（002） |
| `/tables/{table_id}/artifacts` | 200 | 関連 ref 一覧（OpenAPI 上は 404 未列挙。実装時は 404 の要否を別途確定） |

---

## 3. 更新履歴（このガイド）

| 日付 | 内容 |
|------|------|
| 2026-04-03 | 初版。SPEC-TI-014 §13.1・OpenAPI 0.1.6 系に整合。 |
| 2026-04-03 | OpenAPI **0.1.7** と **401 表記の完全一致**。§1.3・§2.2・§2.5 を更新（tables / review-points の配線状況を明記）。 |
| 2026-04-03 | **`POST /suggestion-runs` の stale metadata 409** 実装に合わせ §1.7・§2.4 を更新（OpenAPI **0.1.8**）。 |
