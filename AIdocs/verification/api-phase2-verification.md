# API Phase 2 Verification

## 対象
- POST /api/datasets/
- GET /api/datasets/{id}/
- POST /api/datasets/{id}/select-sheet/
- POST /api/datasets/{id}/profile/
- GET /api/datasets/{id}/profile/
- POST /api/datasets/{id}/semantic-mapping/

## 結果
- 実施日: 2026-03-27
- 実施者: Codex + admin
- 対象環境: local docker compose (`http://localhost:8080`)

### 実行シナリオ
1. `POST /api/auth/token/` で token 取得（admin/admin）
2. `POST /api/workspaces/` で workspace 作成
3. `POST /api/datasets/` で CSV アップロード
4. `POST /api/datasets/{id}/select-sheet/`
5. `POST /api/datasets/{id}/profile/` でジョブ投入
6. `GET /api/datasets/{id}/` で `mapping_ready` を確認
7. `GET /api/datasets/{id}/profile/` で profile 結果確認
8. `POST /api/datasets/{id}/semantic-mapping/` で user 修正
9. `GET /api/datasets/{id}/profile/` 再取得で source 反映確認

### APIごとの結果
- `POST /api/datasets/`: 201（`id`, `status`, `sheets` を含む）
- `GET /api/datasets/{id}/`: 200（`status=mapping_ready` を確認）
- `POST /api/datasets/{id}/select-sheet/`: 200
- `POST /api/datasets/{id}/profile/`: 202（`{"enqueued": true}`）
- `GET /api/datasets/{id}/profile/`: 200（row/column/column profiles を確認）
- `POST /api/datasets/{id}/semantic-mapping/`: 200（`{"ok": true}`）

### 補足
- 初期実装では `POST /api/datasets/` のレスポンスが作成用 serializer 形式だったため、Phase 2 検証時に `id` が取れない問題を修正済み。
