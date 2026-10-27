from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

import polib
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, connections, transaction
from django.http import Http404
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.core.models import IdSequence
from apps.volunteers import services
from apps.volunteers.forms import AcceptApplicationForm
from apps.volunteers.models import ApplicationStatus, Team, VolunteerRole

pytestmark = pytest.mark.django_db


@pytest.fixture
def super_admin():
    return User.objects.create_user(
        email="team-admin@example.com", full_name="Team Admin", role=Role.SUPER_ADMIN
    )


@pytest.fixture
def team(reviewer, branch):
    return services.create_team(reviewer, branch.pk, name="Teaching")


def test_t_team_unique_service_and_rename(
    reviewer, branch, branch_factory, super_admin
):
    team = services.create_team(reviewer, branch.pk, name="  Teaching  ")
    assert team.name == "Teaching"
    with pytest.raises(ValidationError, match="already exists"):
        services.create_team(reviewer, branch.pk, name="TEACHING")
    second = services.create_team(reviewer, branch.pk, name="Outreach")
    with pytest.raises(ValidationError, match="already exists"):
        services.rename_team(reviewer, second.pk, name="teaching")
    other = branch_factory(code="BR-LHE-01")
    assert services.create_team(super_admin, other.pk, name="Teaching").branch == other
    assert Team.objects.count() == 3


def test_team_changes_audited_and_preserve_member_links(
    reviewer, team, branch, member_factory
):
    member = member_factory(team=team)
    created = AuditLog.objects.get(action="team.created", entity_id=team.pk)
    assert created.branch_id == branch.pk and created.actor == reviewer
    services.rename_team(reviewer, team.pk, name="Mentoring")
    renamed = AuditLog.objects.filter(action="team.updated").latest("pk")
    assert renamed.before == {"name": "Teaching"}
    assert renamed.after == {"name": "Mentoring"}
    services.deactivate_team(reviewer, team.pk)
    deactivated = AuditLog.objects.filter(action="team.updated").latest("pk")
    assert deactivated.before == {"is_active": True}
    assert deactivated.after == {"is_active": False}
    member.refresh_from_db()
    team.refresh_from_db()
    assert member.team_id == team.pk and not team.is_active


@pytest.mark.parametrize("operation", ["create", "rename", "deactivate"])
def test_team_service_outside_scope_is_404(reviewer, branch_factory, operation):
    other = branch_factory(code="BR-LHE-01")
    team = Team.objects.create(branch=other, name="Other branch team")
    count = AuditLog.objects.count()
    with pytest.raises(Http404):
        if operation == "create":
            services.create_team(reviewer, other.pk, name="Teaching")
        elif operation == "rename":
            services.rename_team(reviewer, team.pk, name="Changed")
        else:
            services.deactivate_team(reviewer, team.pk)
    team.refresh_from_db()
    assert team.name == "Other branch team" and team.is_active
    assert AuditLog.objects.count() == count


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize("route", ["team-create", "team-edit", "team-deactivate"])
def test_hr_cannot_manage_another_branch(
    client, reviewer, branch_factory, method, route
):
    other = branch_factory(code="BR-LHE-01")
    team = Team.objects.create(branch=other, name="Other branch team")
    client.force_login(reviewer)
    kwargs = {"branch_pk": other.pk} if route == "team-create" else {"pk": team.pk}
    response = getattr(client, method)(
        reverse(route, kwargs=kwargs), {"name": "Changed"}
    )
    assert response.status_code == (
        405 if route == "team-deactivate" and method == "get" else 404
    )
    team.refresh_from_db()
    assert team.name == "Other branch team" and team.is_active


def test_hr_list_is_scoped_and_branch_lead_has_no_controls(
    client, reviewer, team, branch_factory
):
    other = branch_factory(code="BR-LHE-01")
    Team.objects.create(branch=other, name="Hidden team")
    client.force_login(reviewer)
    response = client.get(reverse("team-list"))
    assert "Teaching" in response.text and "Hidden team" not in response.text
    assert reverse("team-create", kwargs={"branch_pk": other.pk}) not in response.text
    reviewer.role = Role.BRANCH_LEAD
    reviewer.save(update_fields=["role"])
    response = client.get(reverse("team-list"))
    assert "Teaching" in response.text and "Hidden team" not in response.text
    assert "Rename team" not in response.text and "Deactivate team" not in response.text
    assert (
        client.post(reverse("team-edit", args=[team.pk]), {"name": "No"}).status_code
        == 403
    )


def test_team_forms_prg_messages_duplicate_error_and_mass_assignment(
    client, reviewer, team, branch, branch_factory
):
    client.force_login(reviewer)
    other = branch_factory(code="BR-LHE-01")
    url = reverse("team-create", kwargs={"branch_pk": branch.pk})
    assert client.get(url).status_code == 200
    response = client.post(
        url, {"name": "Outreach", "branch": other.pk, "is_active": False}
    )
    assert response.status_code == 302 and response.url == reverse("team-list")
    created = Team.objects.get(name="Outreach")
    assert created.branch == branch and created.is_active
    assert "Team created." in client.get(response.url).text
    duplicate = client.post(url, {"name": "TEACHING"})
    assert "name" in duplicate.context["form"].errors
    edit = reverse("team-edit", args=[created.pk])
    assert client.get(edit).context["form"].initial == {"name": "Outreach"}
    duplicate = client.post(edit, {"name": "Teaching"})
    assert "already exists" in duplicate.text
    response = client.post(
        edit, {"name": "Mentoring", "branch": other.pk, "is_active": False}
    )
    assert response.status_code == 302
    assert "Team renamed." in client.get(response.url).text
    created.refresh_from_db()
    assert (
        created.name == "Mentoring" and created.branch == branch and created.is_active
    )
    response = client.post(reverse("team-deactivate", args=[created.pk]))
    assert response.status_code == 302
    assert "Team deactivated." in client.get(response.url).text


def test_t_mem_team_branch_service_and_raw_sql(
    reviewer, application, branch_factory, member_factory
):
    other = branch_factory(code="BR-LHE-01")
    wrong_team = Team.objects.create(branch=other, name="Teaching")
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    with pytest.raises(ValidationError):
        services.accept_application(
            reviewer, application.pk, role_id=role.pk, team_id=wrong_team.pk
        )
    application.refresh_from_db()
    assert application.status == ApplicationStatus.PENDING
    member = member_factory()
    with (
        pytest.raises(IntegrityError, match="members_team_branch_fk"),
        transaction.atomic(),
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE members SET team_id = %s WHERE id = %s",
                [wrong_team.pk, member.pk],
            )
    member.refresh_from_db()
    assert member.team_id is None


@pytest.mark.parametrize("inactive", ["team", "role"])
def test_inactive_choices_rejected_by_form_and_service(
    reviewer, application, team, super_admin, inactive
):
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    if inactive == "team":
        services.deactivate_team(reviewer, team.pk)
    else:
        services.deactivate_volunteer_role(super_admin, role.pk)
    form = AcceptApplicationForm(
        {"team_id": team.pk, "role_id": role.pk}, application=application
    )
    assert not form.is_valid()
    assert ("team_id" if inactive == "team" else "role_id") in form.errors
    with pytest.raises(ValidationError):
        services.accept_application(
            reviewer, application.pk, role_id=role.pk, team_id=team.pk
        )


def test_roles_prg_edit_deactivate_and_ignore_submitted_code(
    client, super_admin, member_factory
):
    client.force_login(super_admin)
    url = reverse("volunteer-role-create")
    assert client.get(url).status_code == 200
    payload = {
        "name_en": "Mentor",
        "name_ur": "رہنما",
        "sort_order": 5,
        "code": "HACKED",
        "is_active": False,
    }
    response = client.post(url, payload)
    assert response.status_code == 302
    assert "Volunteer role created." in client.get(response.url).text
    role = VolunteerRole.objects.get(name_en="Mentor")
    assert role.code == "ROLE-00001" and role.is_active
    event = AuditLog.objects.get(action="volunteer_role.created")
    assert event.actor == super_admin and event.branch_id is None
    assert event.after["code"] == role.code
    member = member_factory(volunteer_role=role)
    url = reverse("volunteer-role-edit", args=[role.pk])
    assert client.get(url).context["form"].initial["name_ur"] == "رہنما"
    response = client.post(
        url, {**payload, "name_en": "Senior mentor", "sort_order": 1}
    )
    assert response.status_code == 302
    assert "Volunteer role updated." in client.get(response.url).text
    event = AuditLog.objects.filter(action="volunteer_role.updated").latest("pk")
    assert event.before == {"name_en": "Mentor", "sort_order": 5}
    assert event.after == {"name_en": "Senior mentor", "sort_order": 1}
    response = client.post(reverse("volunteer-role-deactivate", args=[role.pk]))
    assert response.status_code == 302
    assert "Volunteer role deactivated." in client.get(response.url).text
    role.refresh_from_db()
    member.refresh_from_db()
    assert role.code == "ROLE-00001" and not role.is_active
    assert member.volunteer_role == role


@pytest.mark.parametrize(
    "operation",
    ["create", "rename", "deactivate", "role_create", "role_edit", "role_deactivate"],
)
def test_management_audit_failure_rolls_back(
    reviewer, team, branch, super_admin, operation
):
    before_teams = list(Team.objects.values())
    before_roles = list(VolunteerRole.objects.order_by("pk").values())
    before_sequences = list(IdSequence.objects.order_by("pk").values())
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    with patch(
        "apps.volunteers.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            if operation == "create":
                services.create_team(reviewer, branch.pk, name="Outreach")
            elif operation == "rename":
                services.rename_team(reviewer, team.pk, name="Mentoring")
            elif operation == "deactivate":
                services.deactivate_team(reviewer, team.pk)
            elif operation == "role_create":
                services.create_volunteer_role(
                    super_admin, name_en="Mentor", name_ur="رہنما", sort_order=0
                )
            elif operation == "role_edit":
                services.update_volunteer_role(
                    super_admin,
                    role.pk,
                    name_en="Mentor",
                    name_ur="رہنما",
                    sort_order=0,
                )
            else:
                services.deactivate_volunteer_role(super_admin, role.pk)
    assert list(Team.objects.values()) == before_teams
    assert list(VolunteerRole.objects.order_by("pk").values()) == before_roles
    assert list(IdSequence.objects.order_by("pk").values()) == before_sequences


def test_management_server_rejects_invalid_fields(
    client, reviewer, branch, super_admin
):
    client.force_login(reviewer)
    response = client.post(
        reverse("team-create", kwargs={"branch_pk": branch.pk}), {"name": " "}
    )
    assert "name" in response.context["form"].errors
    client.force_login(super_admin)
    response = client.post(
        reverse("volunteer-role-create"),
        {"name_en": "Mentor", "name_ur": "رہنما", "sort_order": -1},
    )
    assert "sort_order" in response.context["form"].errors


@pytest.mark.parametrize("operation", ["create", "edit"])
def test_role_service_validation_errors_are_shown_on_form(
    client, super_admin, operation
):
    client.force_login(super_admin)
    role = VolunteerRole.objects.get(code="VOLUNTEER")
    url = (
        reverse("volunteer-role-create")
        if operation == "create"
        else reverse("volunteer-role-edit", args=[role.pk])
    )
    response = client.post(
        url,
        {
            "name_en": "Mentor",
            "name_ur": "رہنما",
            "sort_order": 2**63,
        },
    )
    assert response.status_code == 200
    assert "sort_order" in response.context["form"].errors
    assert not VolunteerRole.objects.filter(name_en="Mentor").exists()


def test_urdu_management_pages(client, reviewer, team, super_admin, settings, tmp_path):
    compiled = tmp_path / "ur" / "LC_MESSAGES" / "django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(
        str(settings.BASE_DIR / "locale/ur/LC_MESSAGES/django.po")
    ).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    client.force_login(reviewer)
    response = client.get("/ur/app/teams/")
    assert response.status_code == 200 and 'dir="rtl"' in response.text
    assert "ٹیمیں" in response.text
    client.force_login(super_admin)
    response = client.get("/ur/app/volunteer-roles/")
    assert response.status_code == 200 and "رضاکارانہ کردار" in response.text


@pytest.mark.django_db(transaction=True)
def test_t_team_unique_concurrent_create(reviewer, branch):
    barrier = Barrier(2)

    def create(name):
        try:
            barrier.wait(timeout=10)
            try:
                services.create_team(reviewer, branch.pk, name=name)
            except ValidationError:
                return "duplicate"
            return "created"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, ["Teaching", "TEACHING"]))
    assert sorted(results) == ["created", "duplicate"]
    assert Team.objects.filter(branch=branch).count() == 1
    assert AuditLog.objects.filter(action="team.created").count() == 1
