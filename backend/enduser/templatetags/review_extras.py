import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def as_json(value) -> str:
    """dict を整形 JSON として表示用に（監査ログはサーバ生成のため mark_safe）。"""
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return mark_safe(text)
