"""Remote browser runs must never permit domain writes, even on redirects."""

from urllib.parse import urlsplit

import pytest

from tests.e2e.conftest import LOCAL_HOSTS, remote_request_allowed


@pytest.mark.parametrize(
    "method,url,allowed",
    [
        ("GET", "https://demo.example/en/", True),
        ("HEAD", "https://demo.example/health", True),
        ("POST", "https://demo.example/en/accounts/login/", True),
        ("POST", "https://demo.example/ur/accounts/login/", True),
        ("POST", "https://other.example/en/accounts/login/", False),
        ("POST", "http://demo.example/en/accounts/login/", False),
        ("POST", "https://demo.example/en/get-involved/", False),
        ("POST", "https://demo.example/en/app/reports/1/approve/", False),
        ("DELETE", "https://demo.example/en/app/members/1/", False),
    ],
)
def test_remote_e2e_blocks_application_writes(method, url, allowed):
    assert remote_request_allowed(method, url, "https://demo.example") is allowed


@pytest.mark.parametrize(
    "url,local",
    [
        ("http://localhost:8000", True),
        ("http://127.0.0.1:8000", True),
        ("http://[::1]:8000", True),
        ("https://localhost.example", False),
        ("https://localhost@render.example", False),
        ("https://render.example/localhost", False),
    ],
)
def test_write_journeys_require_an_exact_loopback_host(url, local):
    assert (urlsplit(url).hostname in LOCAL_HOSTS) is local
