import csv
import shutil
from datetime import datetime

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.selectors import verify_chain
from apps.core import clock
from apps.core.models import IdSequence
from apps.finance.models import Collection, WeeklyReport
from apps.seed.importer import import_sample_data
from apps.volunteers.models import Application, Member

pytestmark = pytest.mark.django_db


def test_sample_import_replays_services_and_keeps_chronological_audit():
    before = clock.now()
    import_sample_data(settings.BASE_DIR / "sample_data")
    assert clock.now() == before
    assert User.objects.count() == 8
    assert Member.objects.count() == 12
    assert Application.objects.count() == 8
    assert Collection.objects.count() == 15
    assert WeeklyReport.objects.count() == 10
    assert IdSequence.objects.get(key="member:2026").last_value == 12
    assert IdSequence.objects.get(key="application:2026").last_value == 8
    assert Application.objects.get(reference="APP-2026-00008").possible_duplicate
    imported = Member.objects.get(member_id="M-2026-00001")
    assert imported.created_by is None
    assert imported.created_at == datetime.fromisoformat("2026-07-05T10:00:00+05:00")
    event = AuditLog.objects.get(action="member.created", entity_id=imported.pk)
    assert event.metadata == {"source": "spreadsheet import"}
    occurred = list(
        AuditLog.objects.order_by("pk").values_list("occurred_at", flat=True)
    )
    assert occurred == sorted(occurred)
    assert verify_chain() == (True, None)


def test_import_header_error_lists_missing_and_unknown_columns_before_writes(tmp_path):
    shutil.copytree(settings.BASE_DIR / "sample_data", tmp_path / "data")
    path = tmp_path / "data" / "users.csv"
    path.write_text("wrong_email,full_name,role\n", encoding="utf-8")
    with pytest.raises(CommandError) as error:
        call_command("import_sample_data", str(path.parent))
    assert "users.csv" in str(error.value)
    assert "missing columns ['email']" in str(error.value)
    assert "unknown columns ['wrong_email']" in str(error.value)
    assert not User.objects.exists()


def test_import_yaml_maps_alternative_column_names(tmp_path):
    shutil.copytree(settings.BASE_DIR / "sample_data", tmp_path / "data")
    path = tmp_path / "data" / "users.csv"
    path.write_text(
        path.read_text(encoding="utf-8").replace("email,", "login_email,", 1),
        encoding="utf-8",
    )
    mapping = tmp_path / "mapping.yaml"
    mapping.write_text("users.csv:\n  login_email: email\n", encoding="utf-8")
    call_command("import_sample_data", str(path.parent), mapping_path=str(mapping))
    assert User.objects.count() == 8


def test_import_late_failure_rolls_back_all_domain_and_audit_rows(tmp_path):
    shutil.copytree(settings.BASE_DIR / "sample_data", tmp_path / "data")
    path = tmp_path / "data" / "events.csv"
    with path.open("a", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerow(
            ["2026-10-27T09:00:00+05:00", "", "unknown.action", "{}"]
        )
    with pytest.raises(CommandError, match="unknown.action"):
        call_command("import_sample_data", str(path.parent))
    assert not User.objects.exists()
    assert not Member.objects.exists()
    assert not AuditLog.objects.exists()
    assert not IdSequence.objects.exists()
