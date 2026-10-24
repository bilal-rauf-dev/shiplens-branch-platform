import pytest
import time_machine


@pytest.fixture
def clock():
    """Freeze the shared clock without changing the machine's wall clock."""
    with time_machine.travel("2026-10-25T12:00:00+05:00", tick=False) as traveller:
        yield traveller
