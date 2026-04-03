from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ai.client import ping_openai


class Command(BaseCommand):
    help = "OpenAI API疎通確認を行います。"

    def handle(self, *args, **options):
        try:
            result = ping_openai()
        except Exception as exc:  # pragma: no cover
            raise CommandError(f"OpenAI ping failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("status=ok"))
        self.stdout.write(f"model_count={result['model_count']}")
        self.stdout.write(f"sample_models={','.join(result['sample_models'])}")
