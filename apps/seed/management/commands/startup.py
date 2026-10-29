from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Migrate, create the cache table and optionally seed in one Python process."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False, stdout=self.stdout)
        call_command("createcachetable", stdout=self.stdout)
        if settings.DEMO_MODE:
            call_command("seed_demo", if_empty=True, stdout=self.stdout)
