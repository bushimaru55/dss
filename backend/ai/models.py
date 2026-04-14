from django.db import models


class OpenAISettings(models.Model):
    """
    単一行 (pk=1)。環境変数 OPENAI_API_KEY が未設定のときの OpenAI API キー。
    環境変数が優先される。
    """

    api_key = models.CharField(
        "OpenAI API キー",
        max_length=512,
        blank=True,
        help_text="未入力の場合は環境変数 OPENAI_API_KEY を使用します。",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "OpenAI API キー"
        verbose_name_plural = "OpenAI API キー"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
