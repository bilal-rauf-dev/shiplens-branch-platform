from django.core.management.base import BaseCommand, CommandError

from apps.seed.services import seed_demo


class Command(BaseCommand):
    help = "Import the fictional dataset and set demo passwords from the environment."

    def add_arguments(self, parser):
        parser.add_argument("--if-empty", action="store_true")
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        try:
            changed = seed_demo(if_empty=options["if_empty"], reset=options["reset"])
        except Exception as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            "Demo sample data loaded." if changed else "Demo already seeded; skipped."
        )
