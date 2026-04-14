from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class ApiKeyWithPingWidget(forms.TextInput):
    """管理画面用: テキスト入力の右に疎通テストボタンを並べる。"""

    class Media:
        css = {"all": ("admin/css/openai_settings.css",)}

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault("class", "vTextField")
        input_html = super().render(name, value, attrs=attrs, renderer=renderer)
        return format_html(
            '<div class="dss-api-key-inline-row">'
            "{}"
            '<button type="submit" name="_test_key" value="1" class="button">疎通テスト</button>'
            "</div>",
            mark_safe(input_html),
        )
