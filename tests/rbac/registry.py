"""Explicit request recipes for every protected route; extend alongside new routes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.urls import reverse

from apps import audit
from apps.accounts.models import Role, User
from apps.accounts.services import assign_branch
from apps.branches.models import Branch, City
from apps.core import clock
from apps.finance import report_services
from apps.finance import services as finance_services
from apps.finance.report_selectors import week_bounds
from apps.volunteers import services as volunteer_services
from apps.volunteers.forms import ApplicationForm
from apps.volunteers.models import MemberStatus, Team, VolunteerRole
from tests.accounts.conftest import TEST_PASSWORD

NEW_PASSWORD = "Spruce!Harbor-92-Lantern"  # noqa: S105 -- test-only credential.


@dataclass(frozen=True)
class RouteCase:
    method: str
    url_builder: Callable
    fixture_factory: Callable
    expected_success_status: int


def page_url(name, fixture):
    return reverse(name)


REPORT_NARRATIVE = {
    "activities": "Community teaching and support sessions.",
    "volunteer_hours": 12,
    "issues": "",
}


def report_object(scenario):
    fixture = collection_object(scenario)
    branch = fixture["branch"]
    start, _ = week_bounds(clock.today())
    branch.opened_on = start - timedelta(days=7)
    branch.save(update_fields=["opened_on"])
    fixture["report"] = report_services.ensure_drafts(branch)[0]
    fixture["report_lead"] = User.objects.get(email="finance-matrix@example.com")
    fixture["report_reviewer"] = User.objects.create_user(
        email="report-matrix-reviewer@example.com",
        full_name="Report Reviewer",
        role=Role.FINANCE_REVIEWER,
    )
    fixture["data"] = {}
    return fixture


def report_narrative_payload(scenario):
    fixture = report_object(scenario)
    fixture["data"] = REPORT_NARRATIVE
    return fixture


def submitted_report_object(scenario):
    fixture = report_object(scenario)
    report_services.transition(
        fixture["report_lead"], fixture["report"], "submit", narrative=REPORT_NARRATIVE
    )
    fixture["data"] = {"expected_revision": 1, "comment": "Please correct this report"}
    return fixture


def returned_report_object(scenario):
    fixture = submitted_report_object(scenario)
    report_services.transition(
        fixture["report_reviewer"], fixture["report"], "return", **fixture["data"]
    )
    fixture["data"] = REPORT_NARRATIVE
    return fixture


def report_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["report"].pk})


def finance_payload(scenario):
    branch = scenario["branch"]
    branch.status = "ACTIVE"
    branch.save(update_fields=["status"])
    return {
        "branch": branch,
        "data": {
            "collection_date": clock.today(),
            "amount": "100.00",
            "method": "CASH",
            "receipt_no": "MATRIX-1",
            "source_note": "Matrix receipt",
        },
    }


def collection_object(scenario):
    fixture = finance_payload(scenario)
    lead = User.objects.create_user(
        email="finance-matrix@example.com",
        full_name="Finance matrix",
        role=Role.BRANCH_LEAD,
    )
    assign_branch(scenario["admin"], lead, fixture["branch"])
    fixture["collection"] = finance_services.create_collection(
        lead, fixture["branch"], fixture["data"]
    )
    fixture["data"] = {}
    return fixture


def collection_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["collection"].pk})


def collection_create_url(name, fixture):
    return reverse(name, kwargs={"branch_pk": fixture["branch"].pk})


def transfer_payload(scenario):
    fixture = collection_object(scenario)
    fixture["data"] = {
        "collections": [fixture["collection"].pk],
        "transfer_date": clock.today(),
        "bank_reference": "MATRIX-BANK",
        "note": "",
    }
    return fixture


def transfer_object(scenario):
    fixture = collection_object(scenario)
    lead = User.objects.get(email="finance-matrix@example.com")
    fixture["transfer"] = finance_services.create_transfer(
        lead,
        fixture["branch"],
        [fixture["collection"].pk],
        clock.today(),
        "MATRIX-BANK",
    )
    return fixture


def transfer_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["transfer"].pk})


def transfer_prepare_url(name, fixture):
    return reverse(name) + f"?collections={fixture['collection'].pk}"


def collection_edit_payload(scenario):
    fixture = collection_object(scenario)
    fixture["data"] = {
        "collection_date": clock.today(),
        "amount": "101.00",
        "method": "CASH",
        "receipt_no": "MATRIX-1",
        "source_note": "Edited",
    }
    return fixture


def collection_void_payload(scenario):
    fixture = collection_object(scenario)
    fixture["data"] = {"reason": "Duplicate receipt"}
    return fixture


def audit_object(scenario):
    with transaction.atomic():
        event = audit.record(
            scenario["admin"],
            "branch.updated",
            entity=scenario["branch"],
            branch_id=scenario["branch"].pk,
            before={"name_en": "Before"},
            after={"name_en": "After"},
        )
    return {"event": event, "data": {}}


def audit_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["event"].pk})


def transition_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["branch"].pk, "action": "activate"})


def branch_object(scenario):
    return {"branch": scenario["branch"], "data": {}}


def team_object(scenario):
    team = Team.objects.create(branch=scenario["branch"], name="Teaching")
    return {"team": team, "data": {"name": "Community outreach"}}


def team_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["team"].pk})


def team_create_url(name, fixture):
    return reverse(name, kwargs={"branch_pk": fixture["branch"].pk})


def team_create_payload(scenario):
    return {"branch": scenario["branch"], "data": {"name": "Teaching"}}


def volunteer_role_payload(scenario):
    return {
        "volunteer_role": VolunteerRole.objects.get(code="VOLUNTEER"),
        "data": {"name_en": "Mentor", "name_ur": "رہنما", "sort_order": 4},
    }


def volunteer_role_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["volunteer_role"].pk})


def application_object(scenario):
    """Use a valid Pending applicant in the actor's assigned branch."""
    form = ApplicationForm(
        {
            "full_name": "Matrix Applicant",
            "email": "matrix-applicant@example.com",
            "phone": "03001234567",
            "date_of_birth": "2000-01-01",
            "preferred_branch": scenario["branch"].pk,
            "interests": ["education"],
            "availability": ["weekends"],
            "motivation": "I would like to volunteer in my local community.",
            "preferred_language": "en",
            "privacy_consent": True,
        }
    )
    assert form.is_valid(), form.errors
    application = volunteer_services.submit_application(form.cleaned_data, None)
    target = Branch.objects.create(
        code="BR-LHE-01",
        city=City.objects.get(code="LHE"),
        name_en="Other branch",
        name_ur="دوسری شاخ",
    )
    return {
        "application": application,
        "target_branch": target,
        "volunteer_role": VolunteerRole.objects.get(code="VOLUNTEER"),
        "data": {},
    }


def application_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["application"].pk})


def accept_payload(scenario):
    fixture = application_object(scenario)
    fixture["data"] = {"role_id": fixture["volunteer_role"].pk}
    return fixture


def decline_payload(scenario):
    fixture = application_object(scenario)
    fixture["data"] = {"reason": "No capacity at present"}
    return fixture


def reassign_payload(scenario):
    fixture = application_object(scenario)
    fixture["data"] = {"branch_id": fixture["target_branch"].pk}
    return fixture


def member_object(scenario):
    fixture = application_object(scenario)
    reviewer = User.objects.create_user(
        email="matrix-reviewer@example.com",
        full_name="Matrix Reviewer",
        role=Role.HR_LEAD,
    )
    assign_branch(scenario["admin"], reviewer, scenario["branch"])
    fixture["member"] = volunteer_services.accept_application(
        reviewer, fixture["application"].pk, role_id=fixture["volunteer_role"].pk
    )
    return fixture


def member_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["member"].pk})


def member_edit_payload(scenario):
    fixture = member_object(scenario)
    fixture["data"] = {
        "team_id": "",
        "role_id": fixture["volunteer_role"].pk,
        "phone": "+923001234567",
        "notes": "Updated matrix member",
    }
    return fixture


def inactive_member_object(scenario):
    fixture = member_object(scenario)
    member = fixture["member"]
    member.status = MemberStatus.INACTIVE
    member.save(update_fields=["status"])
    return fixture


def left_member_object(scenario):
    fixture = member_object(scenario)
    member = fixture["member"]
    member.status, member.left_on = MemberStatus.LEFT, member.joined_on
    member.save(update_fields=["status", "left_on"])
    fixture["data"] = {"reason": "Returning to volunteer"}
    return fixture


def member_left_payload(scenario):
    fixture = member_object(scenario)
    fixture["data"] = {"left_on": fixture["member"].joined_on.isoformat()}
    return fixture


def branch_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["branch"].pk})


def city_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["city"].pk})


def city_object(scenario):
    return {"city": scenario["branch"].city, "data": {}}


def create_city_payload(scenario):
    return {"data": {"code": "ZZZ", "name_en": "New City", "name_ur": "نیا شہر"}}


def edit_city_payload(scenario):
    return {
        "city": scenario["branch"].city,
        "data": {"name_en": "Edited City", "name_ur": "تبدیل شدہ شہر"},
    }


def create_branch_payload(scenario):
    return {
        "data": {
            "city": City.objects.get(code="ISB").pk,
            "name_en": "New Branch",
            "name_ur": "نئی شاخ",
            "address_en": "",
            "address_ur": "",
            "phone": "",
            "email": "",
        }
    }


def edit_branch_payload(scenario):
    return {
        "branch": scenario["branch"],
        "data": {
            "name_en": "Edited Branch",
            "name_ur": "تبدیل شدہ شاخ",
            "address_en": "",
            "address_ur": "",
            "phone": "",
            "email": "",
        },
    }


def user_url(name, fixture):
    return reverse(name, kwargs={"pk": fixture["target"].pk})


def assignment_url(name, fixture):
    return reverse(
        name,
        kwargs={
            "pk": fixture["target"].pk,
            "branch_id": fixture["branch"].pk,
        },
    )


def no_object(scenario):
    return {"data": {}}


def user_object(scenario):
    # User administration has GLOBAL scope. Never target the only active admin.
    target = User.objects.create_user(
        email="rbac-target@example.com",
        full_name="Target Operator",
        role=Role.BRANCH_LEAD,
    )
    return {"target": target, "data": {}}


def inactive_user_object(scenario):
    target = User.objects.create_user(
        email="rbac-target@example.com",
        full_name="Inactive Operator",
        role=Role.BRANCH_LEAD,
        is_active=False,
    )
    return {"target": target, "data": {}}


def create_payload(scenario):
    return {
        "data": {
            "email": "rbac-created@example.com",
            "full_name": "Created Operator",
            "role": Role.HR_LEAD,
        }
    }


def edit_payload(scenario):
    fixture = user_object(scenario)
    fixture["data"] = {"full_name": "Edited Operator", "role": Role.HR_LEAD}
    return fixture


def assignment_payload(scenario):
    fixture = user_object(scenario)
    fixture["data"] = {"branch_id": scenario["branch"].pk}
    fixture["branch"] = scenario["branch"]
    return fixture


def assigned_user_object(scenario):
    fixture = assignment_payload(scenario)
    assign_branch(scenario["admin"], fixture["target"], fixture["branch"])
    return fixture


def password_payload(scenario):
    return {
        "data": {
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
    }


def settings_payload(scenario):
    return {
        "data": {
            "collection_lock_days": 3,
            "allow_submit_current_week": True,
            "min_volunteer_age": 17,
            "apply_rate_per_hour": 6,
        }
    }


# The four columns are method, URL builder, in-scope fixture factory and success
# status. Payloads must be valid so a validation error cannot masquerade as denial.
def demo_reset_payload(scenario):
    # The matrix tests authorization; real transactional truncation is covered
    # separately with transaction=True in tests/seed/test_demo.py.
    scenario["settings"].DEMO_MODE = True

    def reset(**kwargs):
        with transaction.atomic():
            audit.record(None, "demo.reset")

    scenario["monkeypatch"].setattr("apps.seed.views.seed_demo", reset)
    return {"data": {}}


ROUTE_CASES = {
    "demo-reset": RouteCase("POST", page_url, demo_reset_payload, 302),
    "report-list": RouteCase("GET", page_url, report_object, 200),
    "report-detail": RouteCase("GET", report_url, report_object, 200),
    "report-review-queue": RouteCase("GET", page_url, report_object, 200),
    "report-save": RouteCase("POST", report_url, report_narrative_payload, 302),
    "report-submit": RouteCase("POST", report_url, report_narrative_payload, 302),
    "report-resubmit": RouteCase("POST", report_url, returned_report_object, 302),
    "report-return": RouteCase("POST", report_url, submitted_report_object, 302),
    "report-approve": RouteCase("POST", report_url, submitted_report_object, 302),
    "transfer-list": RouteCase("GET", page_url, transfer_object, 200),
    "transfer-detail": RouteCase("GET", transfer_url, transfer_object, 200),
    "transfer-create": RouteCase("POST", collection_create_url, transfer_payload, 302),
    "transfer-prepare": RouteCase("GET", transfer_prepare_url, collection_object, 302),
    "collection-list": RouteCase("GET", page_url, collection_object, 200),
    "collection-detail": RouteCase("GET", collection_url, collection_object, 200),
    "collection-create": RouteCase("POST", collection_create_url, finance_payload, 302),
    "collection-edit": RouteCase("POST", collection_url, collection_edit_payload, 302),
    "collection-void": RouteCase("POST", collection_url, collection_void_payload, 302),
    "audit-list": RouteCase("GET", page_url, audit_object, 200),
    "audit-detail": RouteCase("GET", audit_url, audit_object, 200),
    "audit-verify": RouteCase("POST", page_url, audit_object, 302),
    "member-edit": RouteCase("POST", member_url, member_edit_payload, 302),
    "member-deactivate": RouteCase("POST", member_url, member_object, 302),
    "member-reactivate": RouteCase("POST", member_url, inactive_member_object, 302),
    "member-mark-left": RouteCase("POST", member_url, member_left_payload, 302),
    "member-reinstate": RouteCase("POST", member_url, left_member_object, 302),
    "member-list": RouteCase("GET", page_url, member_object, 200),
    "team-list": RouteCase("GET", page_url, no_object, 200),
    "team-create": RouteCase("POST", team_create_url, team_create_payload, 302),
    "team-edit": RouteCase("POST", team_url, team_object, 302),
    "team-deactivate": RouteCase("POST", team_url, team_object, 302),
    "volunteer-role-list": RouteCase("GET", page_url, no_object, 200),
    "volunteer-role-create": RouteCase("POST", page_url, volunteer_role_payload, 302),
    "volunteer-role-edit": RouteCase(
        "POST", volunteer_role_url, volunteer_role_payload, 302
    ),
    "volunteer-role-deactivate": RouteCase(
        "POST", volunteer_role_url, volunteer_role_payload, 302
    ),
    "application-detail": RouteCase("GET", application_url, application_object, 200),
    "application-accept": RouteCase("POST", application_url, accept_payload, 302),
    "application-decline": RouteCase("POST", application_url, decline_payload, 302),
    "application-reassign": RouteCase("POST", application_url, reassign_payload, 302),
    "member-detail": RouteCase("GET", member_url, member_object, 200),
    "branch-transition": RouteCase("POST", transition_url, branch_object, 302),
    "branch-list": RouteCase("GET", page_url, no_object, 200),
    "branch-detail": RouteCase("GET", branch_url, branch_object, 200),
    "branch-create": RouteCase("POST", page_url, create_branch_payload, 302),
    "branch-edit": RouteCase("POST", branch_url, edit_branch_payload, 302),
    "city-list": RouteCase("GET", page_url, no_object, 200),
    "city-create": RouteCase("POST", page_url, create_city_payload, 302),
    "city-edit": RouteCase("POST", city_url, edit_city_payload, 302),
    "user-list": RouteCase("GET", page_url, no_object, 200),
    "user-create": RouteCase("POST", page_url, create_payload, 200),
    "user-detail": RouteCase("GET", user_url, user_object, 200),
    "user-edit": RouteCase("POST", user_url, edit_payload, 302),
    "user-deactivate": RouteCase("POST", user_url, user_object, 302),
    "user-reactivate": RouteCase("POST", user_url, inactive_user_object, 302),
    "user-reset-password": RouteCase("POST", user_url, user_object, 200),
    "user-assign-branch": RouteCase("POST", user_url, assignment_payload, 302),
    "user-remove-branch": RouteCase("POST", assignment_url, assigned_user_object, 302),
    "settings-view": RouteCase("GET", page_url, no_object, 200),
    "settings-update": RouteCase("POST", page_url, settings_payload, 302),
    "account-logout": RouteCase("POST", page_url, no_object, 302),
    "account-change-password": RouteCase("POST", page_url, password_payload, 302),
    "dashboard-head-office": RouteCase("GET", page_url, no_object, 200),
    "dashboard-branch": RouteCase("GET", page_url, no_object, 200),
    "application-list": RouteCase("GET", page_url, no_object, 200),
    "content-list": RouteCase("GET", page_url, no_object, 200),
}
