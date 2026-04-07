"""
table_intelligence テスト用: ``workspace_id`` は ``Workspace.slug`` と一致させ、オーナーを ``user`` にする。

本番では同じ対応（TI の tenant キー = slug）を運用で担保する。
"""

from __future__ import annotations

import pytest
from workspaces.models import Workspace


@pytest.fixture(autouse=True)
def _ensure_ti_workspace_slugs_for_user(user, db):
    for slug, name in (
        ("ws-ti", "TI default"),
        ("ws-test-1", "Test 1"),
        ("ws-1", "WS1"),
        ("ws-e2e", "E2E"),
    ):
        Workspace.objects.update_or_create(
            slug=slug,
            defaults={"name": name, "owner": user},
        )
