from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import Role, User, UserBranchAssignment
from apps.branches.models import BranchStatus
from apps.finance import services


@pytest.fixture(autouse=True)
def finance_clock(clock):
    pass


@pytest.fixture
def branch(branch_factory):
    return branch_factory(status=BranchStatus.ACTIVE)


@pytest.fixture
def bl(branch):
    user = User.objects.create_user(
        email="finance-bl@example.com", full_name="Branch Lead", role=Role.BRANCH_LEAD
    )
    UserBranchAssignment.objects.create(user=user, branch=branch, created_by=user)
    return user


@pytest.fixture
def collection_data():
    return {
        "collection_date": date(2026, 10, 25),
        "amount": Decimal("100.00"),
        "method": "CASH",
        "receipt_no": "R-001",
        "collected_by": None,
        "source_note": "Friday box",
    }


@pytest.fixture
def collection(bl, branch, collection_data):
    return services.create_collection(bl, branch, collection_data)
