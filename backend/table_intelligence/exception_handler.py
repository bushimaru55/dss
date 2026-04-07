"""
012 / 014 向けの最小 ErrorResponse エンベロープ。

``/api/v1/``（table_intelligence のみマウント）のレスポンスに限り、
DRF 既定の JSON に ``error_code`` を付与し、``detail`` を維持する。
他の ``/api/`` ルートは DRF 既定ハンドラのまま。
"""

from __future__ import annotations

from typing import Any

from rest_framework.views import exception_handler as drf_exception_handler


TI_API_PREFIX = "/api/v1/"


def _error_code_for_status(status_code: int, data: Any) -> str:
    if status_code == 404:
        return "TI_NOT_FOUND"
    if status_code == 401:
        return "TI_AUTHENTICATION_REQUIRED"
    if status_code == 403:
        return "TI_PERMISSION_DENIED"
    if status_code == 409:
        return "TI_CONFLICT"
    if status_code == 400:
        if isinstance(data, dict) and data and "detail" not in data:
            return "TI_VALIDATION_ERROR"
        if isinstance(data, dict) and isinstance(data.get("detail"), dict):
            return "TI_VALIDATION_ERROR"
        return "TI_BAD_REQUEST"
    return "TI_ERROR"


def _wrap_error_body(data: Any, *, error_code: str) -> dict[str, Any]:
    """``detail`` を残しつつ ``error_code`` を付与。フィールドエラーは ``errors`` に複写。"""
    if isinstance(data, dict) and "error_code" in data and "detail" in data:
        return data

    out: dict[str, Any] = {"error_code": error_code}

    if not isinstance(data, dict):
        out["detail"] = data
        return out

    if "detail" in data:
        out["detail"] = data["detail"]
        extra = {k: v for k, v in data.items() if k != "detail"}
        if extra:
            out["errors"] = extra
        return out

    out["detail"] = "Validation failed."
    out["errors"] = data
    return out


def table_intelligence_aware_exception_handler(exc, context: dict) -> Any:
    request = context.get("request")
    if request is None or not str(getattr(request, "path", "")).startswith(TI_API_PREFIX):
        return drf_exception_handler(exc, context)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = _error_code_for_status(response.status_code, response.data)
    response.data = _wrap_error_body(response.data, error_code=code)
    return response
