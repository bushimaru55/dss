# API Design Phase 2

## Endpoints

### POST /api/datasets/
ファイルアップロードを受け付ける。

### GET /api/datasets/{id}/
Dataset 詳細取得。

### POST /api/datasets/{id}/select-sheet/
対象シート選択。

### POST /api/datasets/{id}/profile/
profile 生成ジョブ投入。

### GET /api/datasets/{id}/profile/
profile 結果取得。

### POST /api/datasets/{id}/semantic-mapping/
semantic label の保存。
