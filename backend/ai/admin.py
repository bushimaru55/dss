import json
import time
from pathlib import Path

from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from ai.client import ping_openai_with_key
from ai.forms import OpenAISettingsForm
from ai.models import OpenAISettings

# 疎通テスト直後の GET でフォームに再表示する未保存 API キー（リダイレクトで DB 値に戻るのを防ぐ）
SESSION_KEY_API_KEY_DRAFT = "openai_settings_api_key_draft"


def _extract_api_key_from_post(request) -> str:
    """POST から api_key を取る（プレフィックス付き name も考慮）。値は返さず長さのみログ可。"""
    post = request.POST
    if "api_key" in post:
        return (post.get("api_key") or "").strip()
    for k in post:
        if k.endswith("-api_key") or k.endswith("_api_key"):
            return (post.get(k) or "").strip()
    return ""


# region agent log
def _agent_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    """NDJSON debug (no secrets: lengths/bools only)."""
    payload = {
        "sessionId": "cb399a",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    for base in (
        Path(settings.BASE_DIR) / "logs" / "debug-cb399a.log",
        Path(settings.BASE_DIR).parent / ".cursor" / "debug-cb399a.log",
    ):
        try:
            base.parent.mkdir(parents=True, exist_ok=True)
            with open(base, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass


# endregion


@admin.register(OpenAISettings)
class OpenAISettingsAdmin(admin.ModelAdmin):
    # 管理トップの app 一覧では has_module_permission と get_model_perms の両方が効く。
    # スーパーユーザー以外はいずれも「権限なし」扱いになり、AI アプリごと非表示になる。
    form = OpenAISettingsForm
    fields = ("api_key",)

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        # pop しない: 再読み込みでも疎通テスト直後のキーを維持する（保存で save_model が消す）
        draft = request.session.get(SESSION_KEY_API_KEY_DRAFT)
        # region agent log
        _agent_log(
            "H2",
            "ai/admin.py:get_form",
            "session draft read",
            {
                "method": getattr(request, "method", None),
                "draft_present": draft is not None,
                "draft_len": len(draft) if isinstance(draft, str) else None,
                "session_key": request.session.session_key is not None,
            },
        )
        # endregion
        # POST（保存など）ではラップしない。initial にドラフトを混ぜるとバインド時の挙動が崩れる可能性がある。
        if draft is None or request.method not in ("GET", "HEAD"):
            return form_class

        class FormWithDraftApiKey(form_class):
            def __init__(self, *args, **form_kwargs):
                initial = form_kwargs.get("initial")
                merged = dict(initial) if isinstance(initial, dict) else {}
                merged["api_key"] = draft
                form_kwargs["initial"] = merged
                super().__init__(*args, **form_kwargs)
                # region agent log
                v = self.initial.get("api_key", "") if hasattr(self, "initial") else ""
                _agent_log(
                    "H3",
                    "ai/admin.py:FormWithDraftApiKey.__init__",
                    "after super init",
                    {
                        "initial_api_key_len": len(v) if isinstance(v, str) else None,
                        "is_bound": getattr(self, "is_bound", None),
                    },
                )
                # endregion

        FormWithDraftApiKey.__name__ = f"{form_class.__name__}WithDraftApiKey"
        FormWithDraftApiKey.__qualname__ = f"{form_class.__qualname__}WithDraftApiKey"
        return FormWithDraftApiKey

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        request.session.pop(SESSION_KEY_API_KEY_DRAFT, None)
        # region agent log
        _agent_log("H4", "ai/admin.py:save_model", "cleared draft after save", {})
        # endregion

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        if not request.user.is_superuser:
            return False
        return not OpenAISettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = OpenAISettings.objects.get_or_create(pk=1)
        return redirect(reverse("admin:ai_openaisettings_change", args=[obj.pk]))

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method == "POST" and request.POST.get("_test_key"):
            return self._test_key_response(request, object_id)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def _test_key_response(self, request, object_id):
        pk = int(object_id) if object_id is not None else 1
        # region agent log
        post_keys = list(request.POST.keys())
        raw = request.POST.get("api_key") or ""
        _agent_log(
            "H1",
            "ai/admin.py:_test_key_response:entry",
            "POST shape for ping",
            {
                "post_key_count": len(post_keys),
                "has_api_key_field": "api_key" in request.POST,
                "post_keys_suffix": [k for k in post_keys if "api" in k or "key" in k][-12:],
                "api_key_param_len": len(raw),
                "has_test_key": bool(request.POST.get("_test_key")),
            },
        )
        # endregion
        key = _extract_api_key_from_post(request)
        # region agent log
        _agent_log(
            "H1",
            "ai/admin.py:_test_key_response:after_extract",
            "extracted key length",
            {"extracted_len": len(key)},
        )
        # endregion
        if not key:
            row = OpenAISettings.objects.filter(pk=pk).first()
            if row and row.api_key:
                key = row.api_key.strip()
        if not key:
            messages.error(
                request,
                "APIキーが入力されていません。フォームに入力するか、先に保存してください。",
            )
            return HttpResponseRedirect(reverse("admin:ai_openaisettings_change", args=[pk]))
        try:
            result = ping_openai_with_key(key)
            sample = "、".join(result["sample_models"]) if result["sample_models"] else "（取得0件）"
            messages.success(
                request,
                f"疎通成功。モデル数 {result['model_count']} 件。先頭の例: {sample}",
            )
        except Exception as e:
            messages.error(request, f"疎通失敗: {e}")
        # リダイレクト後も入力中のキーを表示する（未保存でも DB 値に戻さない）
        request.session[SESSION_KEY_API_KEY_DRAFT] = key
        request.session.modified = True
        try:
            request.session.save()
        except Exception:
            pass
        # region agent log
        _agent_log(
            "H1",
            "ai/admin.py:_test_key_response:session_set",
            "draft stored",
            {
                "stored_len": len(key),
                "session_modified": getattr(request.session, "modified", None),
                "runId": "post-fix",
            },
        )
        # endregion
        return HttpResponseRedirect(reverse("admin:ai_openaisettings_change", args=[pk]))
