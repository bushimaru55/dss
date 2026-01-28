# AIdocs 参照ルール（Knowledge Link）

## 目的
- 実装/運用の回答は、まず AIdocs を参照して「このリポジトリの真実」を優先する

## 参照の優先順位（読む順）
1) AIdocs/INDEX.md（入口・全体像）
2) AIdocs/environments/（環境差分・接続・制約）
3) AIdocs/runbooks/（作業手順・復旧・デプロイ）
4) AIdocs/systems/（構成・設計・依存関係）
5) AIdocs/faq/（よくある質問・小ネタ）

## 回答の出し方（必須）
- まず「前提（どの環境/どの制約か）」を AIdocs から明示
- 次に「チェックリスト → 手順 → ロールバック」の順で提示
- AIdocs に情報が無い場合は「不足している情報」を列挙して AIdocs 追記候補にする
