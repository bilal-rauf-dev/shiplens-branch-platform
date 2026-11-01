from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from apps.finance.models import WeeklyReport
from apps.finance.report_selectors import active_report_branches
from apps.finance.report_services import ensure_drafts


class Command(BaseCommand):
    help = _("Generate missing weekly report drafts for active branches.")

    def handle(self, *args, **options):
        before = WeeklyReport.objects.count()
        for branch in active_report_branches().iterator():
            ensure_drafts(branch)
        created = WeeklyReport.objects.count() - before
        self.stdout.write(
            _("Created %(count)s weekly report drafts.") % {"count": created}
        )
