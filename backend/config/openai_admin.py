"""管理画面から OpenAI API キー設定へ誘導するビュー（テンプレ上書きに依存しない）。"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from django.urls import reverse


@login_required
@user_passes_test(lambda u: u.is_superuser)
def redirect_openai_api_key_settings(request):
    return redirect(reverse("admin:ai_openaisettings_changelist"))
