"""
DRF 例外（014 / OpenAPI と整合する HTTP ステータス）。

ドメイン層は ``services`` の素朴な例外を投げ、ビューでここにマッピングする。
"""

from __future__ import annotations

from rest_framework.exceptions import APIException


class StaleMetadataConflict(APIException):
    """``POST /suggestion-runs`` で superseded な ``metadata_id`` が指定されたとき（409）。"""

    status_code = 409
    default_detail = (
        "This analysis_metadata has been superseded by a newer version. "
        "Use the latest metadata_id (e.g. from job artifact_refs or lineage)."
    )
    default_code = "stale_metadata"
