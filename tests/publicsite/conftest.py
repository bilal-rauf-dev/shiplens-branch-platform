import pytest

from tests.dashboard.conftest import sample_data  # noqa: F401


@pytest.fixture(autouse=True)
def public_clock(clock):
    clock.move_to("2026-11-01T12:00:00+05:00")
