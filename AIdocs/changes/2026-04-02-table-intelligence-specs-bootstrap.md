# 変更記録: 表インテリジェンス（TI）仕様群の導入と既存 AIdocs との関係

**日付**: 2026-04-02  
**関連**: `00_管理/仕様書作成計画.md`, `specs/table-intelligence/01_foundation/SPEC-TI-{006,009,010}-*.md`

## 概要

表読取・分析提案 AI 向けの **15 本仕様（SPEC-TI-001〜015）** の設計計画と索引を `AIdocs` に追加した。Phase1 着手3本（006 概念版、009、010）を Draft 0.1 として起稿した。

## 既存 AIdocs との位置づけ（差分・移行方針）

| 既存ドキュメント | 役割（現状） | TI 仕様との関係 |
|------------------|--------------|-----------------|
| [systems/datasets-spec.md](../systems/datasets-spec.md) | データセットアップロード・メタデータ等の **実装寄り契約** | TI の **File / Sheet / NormalizedDataset** は概念上ここと接続するが、**フィールド名・ジョブ境界は 006→014→015 で再定義**する。既存仕様は **現行実装の参照** とし、TI Approved 後に **差分を明示的にマージ or 廃止** する。 |
| [systems/profiling-spec.md](../systems/profiling-spec.md) | プロファイル生成の **現行フロー** | TI の **AnalysisMetadata / 候補生成（013）** がプロファイル入力を拡張・置換しうる。**重複定義を避け**、プロファイルの列意味は TI 側の grain・dimensions を **正** とする方針で整合タスクを起票する。 |
| [systems/api-design-phase2.md](../systems/api-design-phase2.md) | Phase2 API の **現在の設計** | TI 014 は **新規または拡張エンドポイント**（アップロード、ジョブ状態、人確認 PATCH 等）を記述する。既存パスとの **後方互換** は Phase4 で 006 の DTO 対応表に落とす。 |
| [systems/task-flow-phase2.md](../systems/task-flow-phase2.md) | タスク／ワークフロー | TI 005（人確認）・011（閾値）と **同一の状態機械** を参照するよう、将来 **本ドキュメントから TI へのリンク** を張る。 |
| [systems/semantic-mapping-spec.md](../systems/semantic-mapping-spec.md) | 意味マッピング | TI 004／010 の **dimensions・見出し** と用語が重なる。**語彙の正本は TI 006＋用語集**、セマンティックマッピングは **下流の適用レイヤ** として位置づけ、重複する列名定義は削除方向。 |
| [verification/*](../verification/) | 検証手順 | TI 008 が **受け入れマトリクス** の正本になる。既存 verification は **現行機能の回帰** を維持し、TI 用ケースは **別ファイルまたはセクション** で追加する。 |

## 移行の原則

1. **単一正本**: 表パイプラインの I/O と列挙は **SPEC-TI-006**（および 009／012）を正とする。
2. **実装先行箇所の扱い**: `backend` や既存 OpenAPI にある名前は **参照のみ** とし、TI Approved 時に **リネームマッピング** を `changes/` に1件ずつ残す。
3. **破壊的変更**: datasets／API Phase2 の **MAJOR** 変更は TI Phase4 完了をゲートの一つとする（運用ルールとして [文書管理規約](../00_管理/文書管理規約.md) に従う）。

## 次アクション（提案）

- SPEC-TI-012 骨格（エラーコード namespace）の起稿
- `datasets-spec.md` と SPEC-TI-006 の **エンティティ対応表** を 1 表で追記（別 changes でも可）
