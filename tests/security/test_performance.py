from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.core import rules
from apps.finance.models import Collection, WeeklyReport
from tests.publicsite.test_pages import PATHS

pytestmark = pytest.mark.django_db


@pytest.fixture
def load_data(sample_data, clock):
    clock.move_to("2026-10-31T23:00:00+05:00")
    admin = User.objects.get(role="SUPER_ADMIN")
    branch = Branch.objects.get(code="BR-KHI-01")
    Collection.objects.bulk_create(
        [
            Collection(
                branch=branch,
                reference=f"COL-PERF-{index}",
                collection_date=date(2026, 10, 31),
                amount=Decimal("10.00"),
                method="CASH",
                receipt_no=f"PERF-{index}",
                created_by=admin,
            )
            for index in range(30)
        ]
    )
    return admin


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("path", PATHS)
def test_public_query_budget(
    client, sample_data, django_assert_max_num_queries, language, path
):
    with django_assert_max_num_queries(6) as captured:
        response = client.get(f"/{language}/{path}")
    assert response.status_code == 200
    assert "<script" not in response.text
    print(f"/{language}/{path}: {len(captured)} queries (budget 6)")


@pytest.mark.parametrize(
    "role,path,budget",
    [
        ("SUPER_ADMIN", "app/dashboard/?period=2026-10", 25),
        ("SUPER_ADMIN", "app/collections/", 10),
        ("BRANCH_LEAD", "app/collections/?state=UNSENT", 10),
        ("SUPER_ADMIN", "report-locked", 12),
        ("SUPER_ADMIN", "report-draft", 12),
        ("BRANCH_LEAD", "report-locked", 12),
        ("BRANCH_LEAD", "report-draft", 12),
    ],
)
def test_staff_query_budget(
    client, load_data, django_assert_max_num_queries, role, path, budget
):
    email = (
        "branchlead.demo@shiplens.test"
        if role == "BRANCH_LEAD"
        else "superadmin.demo@shiplens.test"
    )
    user = User.objects.get(email=email)
    client.force_login(user)
    client.get("/en/")
    if path.startswith("report-"):
        week = "2026-10-05" if path == "report-locked" else "2026-10-19"
        report = WeeklyReport.objects.get(branch__code="BR-KHI-01", week_start=week)
        path = f"app/reports/{report.pk}/"
    with django_assert_max_num_queries(budget) as captured:
        response = client.get(f"/en/{path}")
    assert response.status_code == 200
    print(f"{role} /en/{path}: {len(captured)} queries (budget {budget})")


def test_rule_snapshots_do_not_leak_between_requests(
    load_data, django_assert_num_queries
):
    from apps.core.models import SystemSetting

    with rules.request_snapshot(), django_assert_num_queries(1):
        assert rules.get("collection_lock_days") == 7
        assert (
            rules.get_many(["collection_lock_days", "min_volunteer_age"])[
                "collection_lock_days"
            ]
            == 7
        )
        assert rules.get("collection_lock_days") == 7
    SystemSetting.objects.create(
        key="collection_lock_days", value=3, updated_by=load_data
    )
    with rules.request_snapshot(), django_assert_num_queries(1):
        assert rules.get("collection_lock_days") == 3
    assert rules.get("collection_lock_days") == 3


class PageAssets(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.preloads = []
        self.images = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "link" and values.get("rel") == "preload":
            self.preloads.append(values)
        if tag == "img":
            self.images.append(values)


@pytest.mark.parametrize(
    "language,fonts",
    [("en", ["roboto-400", "roboto-500"]), ("ur", ["noto-naskh-arabic-400"])],
)
def test_only_active_language_fonts_are_preloaded(client, sample_data, language, fonts):
    page = PageAssets(client.get(f"/{language}/").text)
    assert len(page.preloads) == len(fonts)
    for preload, font in zip(page.preloads, fonts, strict=True):
        assert font in preload["href"]
        assert preload["as"] == "font"


def test_cms_images_are_small_minified_and_have_dimensions(client, sample_data):
    images = Path(settings.BASE_DIR, "static/img/cms").glob("*.svg")
    for image in images:
        text = image.read_text(encoding="utf-8").strip()
        assert "\n" not in text and "<!--" not in text
        assert image.stat().st_size < 60 * 1024
    client.force_login(User.objects.get(role="SUPER_ADMIN"))
    for path in (
        "/en/",
        "/en/programs/",
        "/en/programs/education-support/",
        "/en/app/content/create/",
    ):
        page = PageAssets(client.get(path).text)
        assert page.images
        for image in page.images:
            assert int(image["width"]) > 0 and int(image["height"]) > 0


def test_assignment_snapshot_is_invalidated_on_revoke_and_add(load_data):
    from apps.accounts.permissions import assigned_branch_ids, request_scope_snapshot
    from apps.accounts.services import assign_branch, remove_branch_assignment

    user = User.objects.get(email="branchlead.demo@shiplens.test")
    branch = Branch.objects.get(code="BR-KHI-01")
    with request_scope_snapshot():
        assert list(assigned_branch_ids(user)) == [branch.pk]
        remove_branch_assignment(load_data, user, branch.pk)
        assert not assigned_branch_ids(user).exists()
        assign_branch(load_data, user, branch)
        assert list(assigned_branch_ids(user)) == [branch.pk]
    remove_branch_assignment(load_data, user, branch.pk)
    with request_scope_snapshot():
        assert not assigned_branch_ids(user).exists()
