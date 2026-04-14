"""指定ユーザーをスーパーユーザーにする（管理画面でユーザー・グループ・AI・APIキーが見えるようにする）。"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant is_staff and is_superuser to an existing user (by username)."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="User username")

    def handle(self, *args, **options):
        username = options["username"].strip()
        User = get_user_model()
        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist as e:
            raise CommandError(f"No user with username={username!r}") from e
        u.is_staff = True
        u.is_superuser = True
        u.is_active = True
        u.save()
        self.stdout.write(
            self.style.SUCCESS(f"Updated {username!r}: is_staff=True, is_superuser=True")
        )
