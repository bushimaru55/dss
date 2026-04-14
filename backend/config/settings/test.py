"""
pytest / CI 用の軽量設定（PostgreSQL 不要で Django DB テストを回す）。

本番・docker 開発は引き続き ``config.settings.local`` / ``prod`` を使用すること。
"""

from .base import *  # noqa: F403, F401

# CI / SQLite テストでは Redis を要求しない（パイプラインはインライン）
TI_TABLE_INTELLIGENCE_PIPELINE_SYNC = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# テストで JSONL をリポジトリ直下に汚さない
ANALYSIS_AUDIT_LOG_PATH = BASE_DIR / "logs" / "analysis_audit_test.jsonl"
