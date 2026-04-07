"""
014 §14 / 015: workspace スコープ（MVP）。

``table_intelligence`` の ``workspace_id`` は **workspaces.Workspace.slug** と同一文字列である前提で照合する。
厳密な membership / RLS は後続（複数メンバー・招待制）。

越境アクセスは **404 でマスク**（単一クエリで PK + workspace を絞り、存在有無を区別しない）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet
from django.http import Http404
from workspaces.models import Workspace

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


def get_accessible_workspace_ids(user: AbstractBaseUser) -> frozenset[str]:
    """ユーザーがアクセス可能な workspace_id（現状は **所有 Workspace の slug** のみ）。"""
    if not user.is_authenticated:
        return frozenset()
    return frozenset(
        Workspace.objects.filter(owner_id=user.pk).values_list("slug", flat=True)
    )


def require_workspace_access(user: AbstractBaseUser, workspace_id: str) -> None:
    if workspace_id not in get_accessible_workspace_ids(user):
        raise Http404()


def scoped_filter(qs: QuerySet, user: AbstractBaseUser, *, workspace_field: str = "workspace_id") -> QuerySet:
    """``workspace_id``（または ``workspace_field``）がユーザーのAccessibleに含まれる行のみ。"""
    wids = get_accessible_workspace_ids(user)
    if not wids:
        return qs.none()
    return qs.filter(**{f"{workspace_field}__in": wids})
