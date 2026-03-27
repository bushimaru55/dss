# Django App Structure

## 方針
Django を modular monolith として構成し、責務ごとに app を分離する。

## app 一覧

| app | 役割 |
|---|---|
| accounts | 認証、ユーザー |
| workspaces | 組織 / ワークスペース |
| datasets | ファイルアップロード、データセット管理 |
| profiling | 行列情報、型推定 |
| semantic_mapping | 列意味推定 |
| suggestions | 活用候補提案 |
| execution_plans | 実行方針 |
| analysis_runs | 実行結果、履歴 |
| reports | レポート生成 |
| ai | AI クライアント抽象化 |
| common | 共通基盤 |

## app 内の責務分離
各 app は可能な限り次のファイルを持つ。
- `models.py`
- `views.py`
- `serializers.py`
- `services.py`
- `selectors.py`
- `tasks.py`
- `urls.py`
- `admin.py`

## services / selectors / tasks
- services: 更新系ロジック
- selectors: 参照系ロジック
- tasks: 非同期処理
