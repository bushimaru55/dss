# aIdocs 参照ルール（Knowledge Link）

## 目的
- 実装/運用の回答は、まず aIdocs を参照して「このリポジトリの真実」を優先する

## 参照の優先順位（読む順）
1) aIdocs/INDEX.md（入口・全体像）
2) aIdocs/environments/（環境差分・接続・制約）
3) aIdocs/runbooks/（作業手順・復旧・デプロイ）
4) aIdocs/systems/（構成・設計・依存関係）
5) aIdocs/faq/（よくある質問・小ネタ）

## 回答の出し方（必須）
- まず「前提（どの環境/どの制約か）」を aIdocs から明示
- 次に「チェックリスト → 手順 → ロールバック」の順で提示
- aIdocs に情報が無い場合は「不足している情報」を列挙して aIdocs 追記候補にする
