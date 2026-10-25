import pytest

from apps.accounts.models import Role, User

TEST_PASSWORD = "Wicker!Forest-72-Prism"  # noqa: S105 -- test-only credential.


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="operator@example.com",
        password=TEST_PASSWORD,
        full_name="Test Operator",
        role=Role.SUPER_ADMIN,
    )


@pytest.fixture
def signed_in(client, user, clock):
    response = client.post(
        "/en/accounts/login/", {"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 302
    return client
