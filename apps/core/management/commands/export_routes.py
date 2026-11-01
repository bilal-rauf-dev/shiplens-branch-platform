from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.route_docs import render_routes


class Command(BaseCommand):
    help = "Write docs/api.md from the URL resolver and permission registry."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path)

    def handle(self, *args, **options):
        path = options["output"] or settings.BASE_DIR / "docs" / "api.md"
        path.write_text(render_routes(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {path.name}"))
