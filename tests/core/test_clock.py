from datetime import date, datetime

from apps.core import clock as business_clock


def test_t_clock_pkt(clock):
    clock.move_to("2026-10-25T20:30:00+00:00")

    assert business_clock.now() == datetime.fromisoformat("2026-10-26T01:30:00+05:00")
    assert business_clock.now().utcoffset().total_seconds() == 18000
    assert business_clock.today() == date(2026, 10, 26)
