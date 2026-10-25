import pytest

from apps.core.net import client_ip, client_ip_key


@pytest.mark.parametrize(
    "forwarded,remote,hops,expected",
    [
        ("198.51.100.1, 203.0.113.5", "10.0.0.1", 1, "203.0.113.5"),
        ("spoofed, 203.0.113.5", "10.0.0.1", 1, "203.0.113.5"),
        ("192.0.2.8, 203.0.113.5, 10.0.0.2", "10.0.0.1", 2, "203.0.113.5"),
        ("192.0.2.8", "10.0.0.1", 2, "10.0.0.1"),
        ("192.0.2.8, invalid", "10.0.0.1", 1, "10.0.0.1"),
        ("", "127.0.0.1", 1, "127.0.0.1"),
        (None, "127.0.0.1", 1, "127.0.0.1"),
        ("192.0.2.8", "127.0.0.1", 0, "127.0.0.1"),
        ("192.0.2.8, 2001:0db8::1", "::1", 1, "2001:db8::1"),
        ("bad", "bad", 1, None),
        (None, None, 1, None),
    ],
)
def test_client_ip_uses_only_trusted_right_hop(
    rf, settings, forwarded, remote, hops, expected
):
    settings.TRUSTED_PROXY_HOPS = hops
    request = rf.get("/", HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR=remote)

    assert client_ip(request) == expected
    assert client_ip_key("applications", request) == (expected or "")
