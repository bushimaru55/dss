# cursor-env
Cursor の Rules / Commands / Subagents / Skills と AIdocs（運用ナレッジ）を Git で管理するリポジトリ。

## 方針
- 秘密情報（APIキー/トークン/パスワード/個人情報）は置かない
- 手順は「チェック → 手順 → ロールバック」で統一

## 使い方は1.2お好きな方で

1)各プロジェクトのルートに **.cursor** と **AIdocs** をコピーするだけ。
```bash
cd /path/to/your-project
cp -a /path/to/cursor-env/.cursor .
cp -a /path/to/cursor-env/AIdocs .


2) リポジトリから取得してコピー（毎回これでもOK）
git clone <cursor-env-repo-url> /tmp/cursor-env
cd /path/to/your-project
cp -a /tmp/cursor-env/.cursor .
cp -a /tmp/cursor-env/AIdocs .
