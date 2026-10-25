from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.permission_docs import render_permissions


class Command(BaseCommand):
    help = "Write docs/permissions.md from the central permission matrix."

    def handle(self, *args, **options):
        path = settings.BASE_DIR / "docs" / "permissions.md"
        path.write_text(render_permissions(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS("Wrote docs/permissions.md"))
