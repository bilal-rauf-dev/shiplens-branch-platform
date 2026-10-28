from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import date, datetime

import pytest

from apps.core import clock as business_clock


def test_t_clock_pkt(clock):
    clock.move_to("2026-10-25T20:30:00+00:00")

    assert business_clock.now() == datetime.fromisoformat("2026-10-26T01:30:00+05:00")
    assert business_clock.now().utcoffset().total_seconds() == 18000
    assert business_clock.today() == date(2026, 10, 26)


def test_clock_override_restores_nested_contexts_and_exceptions(clock):
    original = business_clock.now()
    historical = datetime.fromisoformat("2026-07-01T09:00:00+05:00")
    with business_clock.frozen_at(historical):
        assert business_clock.now() == historical
        assert business_clock.today() == date(2026, 7, 1)
        with pytest.raises(RuntimeError), business_clock.frozen_at(original):
            assert business_clock.now() == original
            raise RuntimeError("historical event failed")
        assert business_clock.now() == historical
    assert business_clock.now() == original


def test_clock_override_is_context_and_thread_local(clock):
    original = business_clock.now()
    historical = datetime.fromisoformat("2026-07-01T09:00:00+05:00")
    isolated = copy_context()
    with business_clock.frozen_at(historical):
        assert isolated.run(business_clock.now) == original
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(business_clock.now).result() == original
        assert business_clock.now() == historical


def test_clock_override_rejects_naive_datetime():
    with pytest.raises(ValueError, match="aware datetime"):
        with business_clock.frozen_at(datetime(2026, 7, 1)):
            pass
