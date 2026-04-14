from django import forms

from ai.models import OpenAISettings
from ai.widgets import ApiKeyWithPingWidget


class OpenAISettingsForm(forms.ModelForm):
    class Meta:
        model = OpenAISettings
        fields = ("api_key",)
        widgets = {
            "api_key": ApiKeyWithPingWidget(
                attrs={
                    "autocomplete": "off",
                    "spellcheck": "false",
                }
            ),
        }
