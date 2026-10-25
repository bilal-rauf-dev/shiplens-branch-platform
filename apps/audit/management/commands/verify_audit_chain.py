from django.core.management.base import BaseCommand, CommandError

from apps.audit.selectors import verify_chain


class Command(BaseCommand):
    help = "Verify the append-only audit hash chain."

    def handle(self, *args, **options):
        ok, first_bad_id = verify_chain()
        if not ok:
            raise CommandError(f"Audit chain is invalid at row {first_bad_id}.")
        self.stdout.write(self.style.SUCCESS("Audit chain is valid."))
