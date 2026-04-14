"""
開発・ローカル検証用: スーパーユーザー admin123 / admin123 を作成または上書きする。

本番では実行しないこと。パスワードは平文相当のため履歴にも残りやすい。
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update superuser admin123 with password admin123."

    def handle(self, *args, **options):
        User = get_user_model()
        u, created = User.objects.get_or_create(
            username="admin123",
            defaults={
                "email": "admin123@localhost",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        u.email = "admin123@localhost"
        u.is_staff = True
        u.is_superuser = True
        u.set_password("admin123")
        u.save()
        self.stdout.write(
            self.style.SUCCESS(
                "Superuser 'admin123' %s. Login with password 'admin123'."
                % ("created" if created else "updated")
            )
        )
