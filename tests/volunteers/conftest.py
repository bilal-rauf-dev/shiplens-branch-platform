import pytest
from django.core.cache import cache

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.branches.models import BranchStatus
from apps.volunteers import services
from apps.volunteers.forms import ApplicationForm, render_token
from apps.volunteers.models import Member, VolunteerRole


@pytest.fixture(autouse=True)
def public_form_clock_and_cache(clock, db):
    cache.clear()


@pytest.fixture
def branch(branch_factory):
    return branch_factory(status=BranchStatus.ACTIVE)


@pytest.fixture
def admin():
    return User.objects.create_user(
        email="hr-test@example.com", full_name="Test HR", role=Role.HR_LEAD
    )


@pytest.fixture
def valid_data(branch):
    return {
        "full_name": "Ayesha Khan",
        "email": "AYESHA@EXAMPLE.COM",
        "phone": "0300 1234567",
        "date_of_birth": "2000-01-01",
        "guardian_consent": False,
        "preferred_branch": branch.pk,
        "interests": ["education"],
        "availability": ["weekends"],
        "motivation": "I want to help my community through volunteering.",
        "preferred_language": "en",
        "privacy_consent": True,
        "website": "",
        "render_token": render_token(),
    }


@pytest.fixture
def post_data(valid_data, clock):
    clock.shift(3)
    return valid_data


@pytest.fixture
def member_factory(branch, admin):
    def create(**fields):
        role, _ = VolunteerRole.objects.get_or_create(
            code="VOLUNTEER", defaults={"name_en": "Volunteer", "name_ur": "رضاکار"}
        )
        return Member.objects.create(
            **{
                "member_id": "M-2026-00001",
                "branch": branch,
                "volunteer_role": role,
                "full_name": "Existing Member",
                "email": "existing@example.com",
                "phone": "+923009999999",
                "joined_on": "2026-10-01",
                "created_by": admin,
                "updated_by": admin,
                **fields,
            }
        )

    return create


@pytest.fixture
def reviewer(admin, branch):
    UserBranchAssignment.objects.create(user=admin, branch=branch, created_by=admin)
    return admin


@pytest.fixture
def application_factory(valid_data):
    def create(**fields):
        form = ApplicationForm({**valid_data, **fields})
        assert form.is_valid(), form.errors
        return services.submit_application(form.cleaned_data, None)

    return create


@pytest.fixture
def application(application_factory):
    return application_factory()


@pytest.fixture
def volunteer_role():
    return VolunteerRole.objects.get_or_create(
        code="VOLUNTEER", defaults={"name_en": "Volunteer", "name_ur": "رضاکار"}
    )[0]
