from datetime import date, timedelta
from html.parser import HTMLParser
from time import perf_counter
from urllib.parse import parse_qs, urlsplit

import polib
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import Role, UserBranchAssignment
from apps.core import clock as business_clock
from apps.volunteers import selectors
from apps.volunteers.models import Member, MemberStatus, Team, VolunteerRole
from apps.volunteers.views import MemberListView

pytestmark = pytest.mark.django_db


@pytest.fixture
def register(member_factory, reviewer, branch, branch_factory):
    other_branch = branch_factory(code="BR-LHE-01", name_en="Hidden branch")
    team = Team.objects.create(branch=branch, name="Teaching", is_active=False)
    other_team = Team.objects.create(branch=other_branch, name="Hidden team")
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    other_role = VolunteerRole.objects.get(code="TEAM_LEAD")
    made = []
    for index, fields in enumerate(
        [
            {"full_name": "Ayesha Khan", "email": "ayesha@example.com", "team": team},
            {"full_name": "Hidden Member", "branch": other_branch, "team": other_team},
            {"full_name": "نجف علی", "volunteer_role": other_role},
            {"full_name": "Inactive Member", "status": MemberStatus.INACTIVE},
            {
                "full_name": "Left Member",
                "status": MemberStatus.LEFT,
                "left_on": date(2026, 10, 25),
            },
        ]
    ):
        made.append(
            member_factory(
                **{
                    "member_id": f"M-2026-{index + 1:05d}",
                    "email": f"member{index}@example.com",
                    "phone": f"+92300123456{index}",
                    "joined_on": date(2026, 10, index + 1),
                    "created_at": business_clock.now() + timedelta(seconds=index),
                    **fields,
                }
            )
        )
    return {
        "members": made,
        "team": team,
        "role": role,
        "other_branch": other_branch,
        "other_team": other_team,
    }


@pytest.mark.parametrize(
    "query",
    [
        "AYESHA",
        "YESHA@EXAMPLE",
        "m-2026-00001",
        "0300 123-4560",
        "+92 300 1234560",
        "923001234560",
        "1234560",
    ],
)
def test_t_mem_search_each_field(reviewer, register, query):
    assert list(selectors.search_members(reviewer, {"q": query})) == [
        register["members"][0]
    ]


def test_t_mem_search_urdu(reviewer, register):
    assert list(selectors.search_members(reviewer, {"q": "نجف"})) == [
        register["members"][2]
    ]


@pytest.mark.parametrize(
    "filter_name,expected",
    [
        ("branch", [0, 2]),
        ("team", [0]),
        ("role", [0]),
        ("status", [3]),
        ("joined_from", [2]),
        ("joined_to", [0]),
    ],
)
def test_t_mem_search_filters(reviewer, branch, register, filter_name, expected):
    values = {
        "branch": branch.pk,
        "team": register["team"].pk,
        "role": register["role"].pk,
        "status": MemberStatus.INACTIVE,
        "joined_from": date(2026, 10, 3),
        "joined_to": date(2026, 10, 1),
    }
    result = set(selectors.search_members(reviewer, {filter_name: values[filter_name]}))
    assert result == {register["members"][index] for index in expected}


def test_t_mem_search_combined_filters(client, reviewer, branch, register):
    client.force_login(reviewer)
    params = {
        "q": "ayesha",
        "branch": branch.pk,
        "team": register["team"].pk,
        "role": register["role"].pk,
        "status": "ACTIVE",
        "joined_from": "2026-10-01",
        "joined_to": "2026-10-01",
        "sort": "name",
    }
    response = client.get(reverse("member-list"), params)
    assert response.status_code == 200
    assert list(response.context["members"]) == [register["members"][0]]
    params["joined_from"] = params["joined_to"] = "2026-10-02"
    assert not client.get(reverse("member-list"), params).context["members"]


@pytest.mark.parametrize("role", [Role.BRANCH_LEAD, Role.HR_LEAD])
def test_t_mem_search_scope_and_filter_choices(client, reviewer, register, role):
    reviewer.role = role
    reviewer.save(update_fields=["role"])
    client.force_login(reviewer)
    response = client.get(reverse("member-list"), {"status": ""})
    assert {member.pk for member in response.context["members"]} == {
        member.pk for index, member in enumerate(register["members"]) if index != 1
    }
    assert "Hidden Member" not in response.text and "Hidden team" not in response.text
    assert "Hidden branch" not in response.text
    assert list(selectors.search_members(reviewer, {"q": "Hidden"})) == []
    for field, pk in [
        ("branch", register["other_branch"].pk),
        ("team", register["other_team"].pk),
    ]:
        response = client.get(reverse("member-list"), {field: pk})
        assert field in response.context["filter_form"].errors
        assert not response.context["members"]


def test_t_mem_search_super_admin_global(client, reviewer, register):
    reviewer.role = Role.SUPER_ADMIN
    reviewer.save(update_fields=["role"])
    client.force_login(reviewer)
    response = client.get(
        reverse("member-list"), {"branch": register["other_branch"].pk}
    )
    assert list(response.context["members"]) == [register["members"][1]]


def test_t_mem_search_revocation_takes_effect(client, reviewer, register):
    client.force_login(reviewer)
    assert client.get(reverse("member-list")).context["members"]
    UserBranchAssignment.objects.filter(user=reviewer).delete()
    response = client.get(reverse("member-list"))
    assert not response.context["members"]
    assert list(selectors.search_members(reviewer, {})) == []


@pytest.mark.parametrize("role", [Role.FINANCE_REVIEWER, Role.CONTENT_EDITOR])
def test_t_mem_search_forbidden_roles(client, reviewer, register, role):
    reviewer.role = role
    reviewer.save(update_fields=["role"])
    client.force_login(reviewer)
    assert client.get(reverse("member-list")).status_code == 403
    assert not selectors.search_members(reviewer, {}).exists()


@pytest.mark.parametrize(
    "params,field",
    [
        ({"joined_from": "not-a-date"}, "joined_from"),
        ({"joined_from": "2026-10-10", "joined_to": "2026-10-01"}, "joined_to"),
        ({"status": "HACKED"}, "status"),
        ({"sort": "email; DROP TABLE members"}, "sort"),
        ({"role": "-1"}, "role"),
        ({"branch": "abc"}, "branch"),
    ],
)
def test_invalid_filters_show_errors_and_no_records(
    client, reviewer, register, params, field
):
    client.force_login(reviewer)
    response = client.get(reverse("member-list"), params)
    assert (
        response.status_code == 200 and field in response.context["filter_form"].errors
    )
    assert not response.context["members"]


@pytest.mark.parametrize(
    "sort,expected",
    [
        ("", [2, 0]),
        ("name", [0, 2]),
        ("-name", [2, 0]),
        ("joined", [0, 2]),
        ("-joined", [2, 0]),
    ],
)
def test_member_sorting(reviewer, register, sort, expected):
    assert list(selectors.search_members(reviewer, {"sort": sort})) == [
        register["members"][index] for index in expected
    ]


class Links(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.links = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href", ""))


def test_t_mem_pagination_preserves_all_filters(
    client, reviewer, branch, member_factory
):
    team = Team.objects.create(branch=branch, name="Teaching")
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    for index in range(26):
        member_factory(
            member_id=f"M-2026-{index + 1:05d}",
            email=f"page{index}@example.com",
            team=team,
            full_name="Ayesha & Co",
        )
    client.force_login(reviewer)
    params = {
        "q": "Ayesha &",
        "branch": str(branch.pk),
        "team": str(team.pk),
        "role": str(role.pk),
        "status": "ACTIVE",
        "joined_from": "2026-10-01",
        "joined_to": "2026-10-25",
        "sort": "name",
    }
    response = client.get(reverse("member-list"), params)
    assert len(response.context["members"]) == 25
    assert response.context["page_obj"].paginator.count == 26
    next_link = next(link for link in Links(response.text).links if "page=2" in link)
    assert parse_qs(urlsplit(next_link).query) == {
        **{key: [value] for key, value in params.items()},
        "page": ["2"],
    }
    second = client.get(reverse("member-list") + next_link)
    assert len(second.context["members"]) == 1
    assert {member.pk for member in second.context["members"]}.isdisjoint(
        member.pk for member in response.context["members"]
    )
    assert second["Cache-Control"] == "no-store, private"
    assert "?" + "&amp;" not in second.text


def test_member_indexes_exist_in_postgresql():
    with connection.cursor() as cursor:
        indexes = connection.introspection.get_constraints(
            cursor, Member._meta.db_table
        )
    for name in (
        "members_branch_joined",
        "members_joined",
        "members_status",
        "members_created",
        "members_name_lower",
        "members_name_trgm",
        "members_email_trgm",
    ):
        assert indexes[name]["index"]
    for field in ("team_id", "volunteer_role_id", "member_id"):
        assert any(
            index["columns"] == [field] and (index["index"] or index["unique"])
            for index in indexes.values()
        )
    assert indexes["members_name_trgm"]["type"] == "gin"
    assert indexes["members_email_trgm"]["type"] == "gin"


def test_member_list_urdu_and_mobile_labels(
    client, reviewer, register, settings, tmp_path
):
    compiled = tmp_path / "ur/LC_MESSAGES/django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(
        str(settings.BASE_DIR / "locale/ur/LC_MESSAGES/django.po")
    ).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    client.force_login(reviewer)
    response = client.get("/ur/app/members/")
    assert response.status_code == 200 and 'dir="rtl"' in response.text
    assert "اراکین" in response.text
    assert "آزمائشی شاخ" in response.text
    assert 'data-label="رکن شناخت"' in response.text
    assert "<script" not in response.text


@pytest.mark.performance
def test_t_mem_search_performance_5000_members(reviewer, branch, rf, record_property):
    """Time the rendered scoped view, excluding fixture setup and middleware."""
    team = Team.objects.create(branch=branch, name="Teaching")
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    Member.objects.bulk_create(
        [
            Member(
                member_id=f"M-2026-{index + 1:05d}",
                branch=branch,
                team=team,
                volunteer_role=role,
                full_name=f"Performance Member {index:05d}",
                email=f"performance{index}@example.com",
                phone=f"+92300{index:07d}",
                joined_on=date(2026, 10, 1),
                created_by=reviewer,
                updated_by=reviewer,
            )
            for index in range(5000)
        ]
    )
    assert Member.objects.count() == 5000
    params = {
        "q": "Performance",
        "branch": branch.pk,
        "team": team.pk,
        "role": role.pk,
        "status": "ACTIVE",
        "joined_from": "2026-10-01",
        "joined_to": "2026-10-01",
        "sort": "name",
    }

    def render():
        request = rf.get(reverse("member-list"), params)
        request.user = reviewer
        return MemberListView.as_view()(request).render()

    render()  # Warm template compilation and connection caches outside the timing.
    with CaptureQueriesContext(connection) as queries:
        start = perf_counter()
        response = render()
        elapsed_ms = (perf_counter() - start) * 1000
    record_property("member_list_ms", round(elapsed_ms, 2))
    record_property("member_list_queries", len(queries))
    assert response.status_code == 200
    assert response.context_data["paginator"].count == 5000
    assert len(response.context_data["members"]) == 25
    assert len(queries) <= 8, list(queries)
    assert elapsed_ms < 300, f"Rendered member list took {elapsed_ms:.2f} ms"
