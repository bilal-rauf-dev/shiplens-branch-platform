from django.core.management.base import BaseCommand, CommandError

from apps.seed.importer import import_sample_data


class Command(BaseCommand):
    help = "Replay an authored CSV dataset through the real domain services."

    def add_arguments(self, parser):
        parser.add_argument("directory")
        parser.add_argument("--mapping", dest="mapping_path")

    def handle(self, *args, **options):
        try:
            counts = import_sample_data(options["directory"], options["mapping_path"])
        except Exception as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Imported sample history: {counts}"))
