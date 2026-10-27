"""Applicant PII stays inside the HR/SA scope on every review path."""

import polib
import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.accounts.selectors import role_home_name
from apps.audit.models import AuditLog
from apps.branches.models import BranchStatus
from apps.volunteers import selectors, services
from apps.volunteers.models import ApplicationStatus, Member, Team

pytestmark = pytest.mark.django_db


@pytest.fixture
def hr_client(client, reviewer):
    client.force_login(reviewer, backend="apps.accounts.backends.EmailBackend")
    return client


@pytest.fixture
def super_admin():
    return User.objects.create_user(
        email="review-super@example.com", full_name="Super Admin", role=Role.SUPER_ADMIN
    )


def url(name, application):
    return reverse(name, kwargs={"pk": application.pk})


def test_t_rbac_scope_app(
    reviewer,
    hr_client,
    application,
    application_factory,
    branch_factory,
    volunteer_role,
):
    lahore = branch_factory(code="BR-LHE-01", name_en="Lahore")
    islamabad = branch_factory(code="BR-ISB-01", name_en="Islamabad")
    UserBranchAssignment.objects.create(
        user=reviewer, branch=lahore, created_by=reviewer
    )
    assigned = application_factory(
        preferred_branch=lahore.pk, email="lahore@example.com"
    )
    foreign = application_factory(
        preferred_branch=islamabad.pk,
        email="private-isb@example.com",
        full_name="Private Islamabad",
    )
    listing = hr_client.get(reverse("application-list"))
    assert listing.status_code == 200
    assert {row.pk for row in listing.context["applications"]} == {
        application.pk,
        assigned.pk,
    }
    assert foreign.reference not in listing.text and foreign.email not in listing.text
    choices = listing.context["filter_form"].fields["branch_id"].queryset
    assert {branch.pk for branch in choices} == {
        application.preferred_branch_id,
        lahore.pk,
    }
    assert hr_client.get(url("application-detail", assigned)).status_code == 200
    hidden = hr_client.get(url("application-detail", foreign))
    missing = hr_client.get(reverse("application-detail", args=[foreign.pk + 999]))
    assert hidden.status_code == missing.status_code == 404
    assert hidden.content == missing.content
    forged_filter = hr_client.get(
        reverse("application-list"), {"branch_id": islamabad.pk}
    )
    assert not list(forged_filter.context["applications"])
    assert foreign.email not in forged_filter.text
    for action, data in [
        ("application-accept", {"role_id": volunteer_role.pk}),
        ("application-decline", {"reason": "Not assigned here"}),
        ("application-reassign", {"branch_id": lahore.pk}),
    ]:
        assert hr_client.post(url(action, foreign), data).status_code == 404


@pytest.mark.parametrize(
    "role", [Role.FINANCE_REVIEWER, Role.CONTENT_EDITOR, Role.BRANCH_LEAD]
)
def test_review_pages_deny_other_roles(client, application, role):
    actor = User.objects.create_user(
        email="denied-review@example.com", full_name="Denied", role=role
    )
    client.force_login(actor, backend="apps.accounts.backends.EmailBackend")
    assert client.get(reverse("application-list")).status_code == 403
    response = client.get(url("application-detail", application))
    assert response.status_code == 403
    assert application.email not in response.text


def test_sa_reads_all_but_cannot_accept_or_decline(
    client, super_admin, application, volunteer_role
):
    client.force_login(super_admin, backend="apps.accounts.backends.EmailBackend")
    assert application.reference in client.get(reverse("application-list")).text
    response = client.get(url("application-detail", application))
    assert response.status_code == 200
    assert url("application-accept", application) not in response.text
    assert url("application-decline", application) not in response.text
    assert url("application-reassign", application) in response.text
    for action, data in [
        ("application-accept", {"role_id": volunteer_role.pk}),
        ("application-decline", {"reason": "Not permitted"}),
    ]:
        assert client.post(url(action, application), data).status_code == 403
    application.refresh_from_db()
    assert (
        application.status == ApplicationStatus.PENDING and not Member.objects.exists()
    )


def test_hr_home_is_the_real_review_list(hr_client, reviewer, application):
    response = hr_client.get(reverse(role_home_name(reviewer)))
    assert response.status_code == 200
    assert application.reference in response.text
    assert "volunteers/application_list.html" in [
        template.name for template in response.templates
    ]


def test_list_tabs_filters_newest_first_and_pagination(
    hr_client, reviewer, application_factory, volunteer_role, clock
):
    applications = []
    for number in range(26):
        applications.append(application_factory(email=f"review-{number}@example.com"))
        clock.shift(1)
    listing = hr_client.get(reverse("application-list"))
    assert listing.context["page_obj"].paginator.count == 26
    assert len(listing.context["applications"]) == 25
    assert listing.context["applications"][0].pk == applications[-1].pk
    second = hr_client.get(reverse("application-list"), {"page": 2})
    assert len(second.context["applications"]) == 1
    services.accept_application(reviewer, applications[0].pk, role_id=volunteer_role.pk)
    services.decline_application(reviewer, applications[1].pk, "No capacity")
    for status, expected in [("ACCEPTED", 1), ("DECLINED", 1), ("PENDING", 24)]:
        response = hr_client.get(reverse("application-list"), {"status": status})
        assert response.context["page_obj"].paginator.count == expected
    invalid = hr_client.get(reverse("application-list"), {"status": "UNKNOWN"})
    assert not list(invalid.context["applications"])


def test_detail_shows_age_history_and_scoped_team_choices(
    hr_client, application, branch_factory
):
    own_team = Team.objects.create(branch=application.preferred_branch, name="Teaching")
    other = branch_factory(code="BR-LHE-01", name_en="Lahore")
    foreign_team = Team.objects.create(branch=other, name="Hidden team name")
    response = hr_client.get(url("application-detail", application))
    assert response.status_code == 200
    assert response.context["age"] == 26
    assert application.date_of_birth.isoformat() not in response.text
    assert "Date of birth" not in response.text
    assert application.email in response.text and application.phone in response.text
    assert "Application submitted" in response.text and "PKT" in response.text
    assert list(response.context["accept_form"].fields["team_id"].queryset) == [
        own_team
    ]
    assert foreign_team.name not in response.text
    assert "no-store" in response["Cache-Control"]


def test_duplicate_application_link_is_scoped(
    hr_client, application, application_factory, branch_factory
):
    related = application_factory(email=application.email)
    response = hr_client.get(url("application-detail", related))
    assert url("application-detail", application) in response.text
    foreign_branch = branch_factory(code="BR-ISB-01", name_en="Islamabad")
    foreign = application_factory(
        preferred_branch=foreign_branch.pk,
        email="foreign-match@example.com",
        phone="03019999999",
    )
    matched = application_factory(email="own-match@example.com", phone=foreign.phone)
    response = hr_client.get(url("application-detail", matched))
    assert "A matched record is outside your access." in response.text
    assert foreign.reference not in response.text and foreign.email not in response.text
    assert url("application-detail", foreign) not in response.text


def test_duplicate_member_has_a_working_scoped_link(
    hr_client, application_factory, member_factory
):
    member = member_factory()
    application = application_factory(email=member.email)
    response = hr_client.get(url("application-detail", application))
    member_url = reverse("member-detail", args=[member.pk])
    assert member_url in response.text
    member_page = hr_client.get(member_url)
    assert member_page.status_code == 200
    assert member.email in member_page.text
    assert "no-store" in member_page["Cache-Control"]


def test_duplicate_member_outside_scope_is_not_exposed(
    hr_client, application_factory, member_factory, branch_factory
):
    foreign_branch = branch_factory(code="BR-ISB-01", name_en="Islamabad")
    member = member_factory(branch=foreign_branch)
    application = application_factory(email=member.email)
    response = hr_client.get(url("application-detail", application))
    assert member.member_id not in response.text
    assert reverse("member-detail", args=[member.pk]) not in response.text
    assert hr_client.get(reverse("member-detail", args=[member.pk])).status_code == 404


def test_accept_post_redirect_get_with_created_member(
    hr_client, application, volunteer_role
):
    response = hr_client.post(
        url("application-accept", application), {"role_id": volunteer_role.pk}
    )
    assert response.status_code == 302 and response.url == url(
        "application-detail", application
    )
    detail = hr_client.get(response.url)
    member = Member.objects.get()
    assert f"Member {member.member_id} created." in detail.text
    assert reverse("member-detail", args=[member.pk]) in detail.text
    assert 'name="role_id"' not in detail.text
    assert f"Member {member.member_id} created." not in hr_client.get(response.url).text


def test_decline_post_redirect_get_and_reason_error(hr_client, application):
    invalid = hr_client.post(url("application-decline", application), {"reason": "bad"})
    assert invalid.status_code == 400 and 'role="alert"' in invalid.text
    assert application.reference in invalid.text
    response = hr_client.post(
        url("application-decline", application), {"reason": "No capacity at present"}
    )
    assert response.status_code == 302
    assert "Application declined." in hr_client.get(response.url).text
    application.refresh_from_db()
    assert application.status == ApplicationStatus.DECLINED


def test_reassign_outside_scope_redirects_to_list(
    hr_client, application, branch_factory
):
    target = branch_factory(code="BR-LHE-01", name_en="Lahore")
    response = hr_client.post(
        url("application-reassign", application), {"branch_id": target.pk}
    )
    assert response.status_code == 302 and response.url == reverse("application-list")
    landing = hr_client.get(response.url)
    assert landing.status_code == 200 and "Application reassigned." in landing.text
    assert application.reference not in landing.text
    assert hr_client.get(url("application-detail", application)).status_code == 404


def test_sa_can_reassign_per_matrix(client, super_admin, application, branch_factory):
    client.force_login(super_admin, backend="apps.accounts.backends.EmailBackend")
    target = branch_factory(code="BR-LHE-01", name_en="Lahore")
    response = client.post(
        url("application-reassign", application), {"branch_id": target.pk}
    )
    assert response.status_code == 302 and response.url == url(
        "application-detail", application
    )


@pytest.mark.parametrize("status", [BranchStatus.PAUSED, BranchStatus.CLOSED])
def test_reassign_form_excludes_unavailable_branches(
    hr_client, application, branch_factory, status
):
    target = branch_factory(code="BR-LHE-01", name_en="Lahore", status=status)
    response = hr_client.post(
        url("application-reassign", application), {"branch_id": target.pk}
    )
    assert response.status_code == 400
    assert not AuditLog.objects.filter(action="application.reassigned").exists()


@pytest.mark.parametrize("action", ["accept", "decline", "reassign"])
def test_terminal_application_actions_return_409(
    hr_client, reviewer, application, volunteer_role, action
):
    services.accept_application(reviewer, application.pk, role_id=volunteer_role.pk)
    data = {
        "role_id": volunteer_role.pk,
        "reason": "Already decided",
        "branch_id": application.preferred_branch_id,
    }
    response = hr_client.post(url(f"application-{action}", application), data)
    assert response.status_code == 409 and 'role="alert"' in response.text
    assert "This application has already been decided." in response.text
    assert Member.objects.count() == 1


def test_foreign_team_and_existing_member_are_form_errors(
    hr_client, application, volunteer_role, branch_factory, member_factory
):
    target = branch_factory(code="BR-LHE-01", name_en="Lahore")
    team = Team.objects.create(branch=target, name="Foreign team")
    response = hr_client.post(
        url("application-accept", application),
        {"role_id": volunteer_role.pk, "team_id": team.pk},
    )
    assert response.status_code == 400
    member_factory(email=application.email)
    response = hr_client.post(
        url("application-accept", application), {"role_id": volunteer_role.pk}
    )
    assert response.status_code == 400
    assert Member.objects.count() == 1
    assert "A current member already uses this email address." in response.text


@pytest.mark.parametrize("action", ["accept", "decline", "reassign"])
def test_review_actions_are_post_only_and_csrf_protected(
    reviewer, application, volunteer_role, action
):
    client = Client(enforce_csrf_checks=True)
    client.force_login(reviewer, backend="apps.accounts.backends.EmailBackend")
    endpoint = url(f"application-{action}", application)
    assert client.get(endpoint).status_code == 405
    response = client.post(
        endpoint,
        {
            "role_id": volunteer_role.pk,
            "reason": "No capacity",
            "branch_id": application.preferred_branch_id,
        },
    )
    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == ApplicationStatus.PENDING


def test_history_selector_denies_roles_outside_entity_permissions(application):
    actor = User.objects.create_user(
        email="finance-history@example.com",
        full_name="Finance",
        role=Role.FINANCE_REVIEWER,
    )
    assert selectors.application_history(actor, application) == []


def test_note_output_is_escaped(hr_client, application_factory):
    application = application_factory(
        motivation="<script>alert(1)</script> Volunteer safely."
    )
    response = hr_client.get(url("application-detail", application))
    assert "<script>" not in response.text and "&lt;script&gt;" in response.text


def test_service_validation_race_is_a_detail_error(
    hr_client, application, branch_factory, monkeypatch
):
    target = branch_factory(code="BR-LHE-01", name_en="Lahore")
    original = services.reassign_branch

    def pause_target(actor, application_id, branch_id):
        target.status = BranchStatus.PAUSED
        target.save(update_fields=["status"])
        return original(actor, application_id, branch_id)

    monkeypatch.setattr(services, "reassign_branch", pause_target)
    response = hr_client.post(
        url("application-reassign", application), {"branch_id": target.pk}
    )
    assert response.status_code == 400
    assert "Choose an Active or Forming branch." in response.text


def test_accept_closed_branch_renders_conflict(hr_client, application, volunteer_role):
    branch = application.preferred_branch
    branch.status = BranchStatus.CLOSED
    branch.save(update_fields=["status"])
    response = hr_client.post(
        url("application-accept", application), {"role_id": volunteer_role.pk}
    )
    assert response.status_code == 409
    assert "This branch is closed" in response.text
    assert not Member.objects.exists()


def test_urdu_review_labels_roles_and_success_message(
    hr_client, application, settings, tmp_path
):
    source = settings.BASE_DIR / "locale" / "ur" / "LC_MESSAGES" / "django.po"
    compiled = tmp_path / "ur" / "LC_MESSAGES" / "django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(str(source)).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    response = hr_client.get(f"/ur/app/applications/{application.pk}/")
    assert response.status_code == 200
    assert "عمر" in response.text and "رضاکار" in response.text
    declined = hr_client.post(
        f"/ur/app/applications/{application.pk}/decline/",
        {"reason": "اس وقت گنجائش نہیں"},
    )
    assert declined.status_code == 302
    assert "درخواست مسترد کر دی گئی۔" in hr_client.get(declined.url).text
