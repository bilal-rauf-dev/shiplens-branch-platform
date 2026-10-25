import pytest
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import Role, User
from apps.accounts.services import assign_branch
from apps.branches.models import Branch
from tests.accounts.conftest import TEST_PASSWORD


@pytest.fixture(scope="session")
def matrix_password_hash():
    """Reuse a real Argon2 test hash; authentication behavior has its own tests."""
    return make_password(TEST_PASSWORD)


@pytest.fixture
def scenario(db, role, matrix_password_hash, clock):
    admin = User.objects.create(
        email="rbac-admin@example.com",
        full_name="Matrix Admin",
        role=Role.SUPER_ADMIN,
        password=matrix_password_hash,
    )
    if role == "ANON":
        actor = AnonymousUser()
    elif role == Role.SUPER_ADMIN:
        actor = admin
    else:
        actor = User.objects.create(
            email=f"rbac-{role.lower()}@example.com",
            full_name="Matrix Operator",
            role=role,
            password=matrix_password_hash,
        )
    branch = Branch.objects.create(code="BR-KHI-01", name_en="Karachi")
    if role in {Role.BRANCH_LEAD, Role.HR_LEAD}:
        assign_branch(admin, actor, branch)
    return {"actor": actor, "admin": admin, "branch": branch}
