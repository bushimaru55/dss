# Preprocessing Foundation Spec (Excel/CSV)

## 目的
壊れ気味の Excel / CSV でも「どこが怪しいか」を可視化し、profiling / semantic mapping の精度を安定化させる。

## 採用ライブラリ
- pandas: CSV/Excel 読込と DataFrame 化
- openpyxl: Excel メタ情報（シート、結合セル、ヘッダ補助）
- pandera: スキーマ検証（汎用 + 売上 + 顧客）
- DuckDB: 今回は未採用（将来 reader の差し替え先）

## 処理フェーズ
1. upload（ファイル保存）
2. sheet listing（Excel のシート列挙）
3. preview（先頭 N 行 + ヘッダ候補 + 警告）
4. profiling（null/unique/sample/type 推定）
5. semantic mapping 候補生成
6. user 修正保存

## 前処理ロジック（MVP）
- 欠損候補統一: `""`, `-`, `N/A`, `null`, `なし`
- 列名正規化:
  - 前後空白、改行、全角空白の除去
  - `Unnamed:*` は補正候補へ
  - 重複列名は `_2`, `_3` サフィックス
- Excel 補正:
  - 結合セル数の検知
  - 空白行/空白列比率
  - ヘッダ候補行推定（最初に非空セルがまとまる行）
  - 2段ヘッダ疑いの警告
- 推定は破壊的変換しない（推定値 + warnings を保存）

## 保存対象
- 元ファイル
- シート情報
- preview JSON
- profiling JSON（列単位）
- semantic mapping JSON
- user 修正結果
- 処理ジョブログ / エラー

## API 下支え
- `POST /api/datasets/`
- `GET /api/datasets/{id}/`
- `GET /api/datasets/{id}/sheets/`
- `GET /api/datasets/{id}/preview/?sheet_id=&rows=`
- `POST /api/datasets/{id}/profile/`
- `GET /api/datasets/{id}/profile/`
- `POST /api/datasets/{id}/semantic-mapping/generate/`
- `GET /api/datasets/{id}/semantic-mapping/`
- `POST /api/datasets/{id}/semantic-mapping/`
