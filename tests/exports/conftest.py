import pytest
from django.core.cache import cache

from tests.dashboard.conftest import AS_OF, sample_data  # noqa: F401


@pytest.fixture(autouse=True)
def export_clock(clock):
    clock.move_to(AS_OF)
    cache.clear()
