"""Remote browser runs must never permit domain writes, even on redirects."""

import io
import runpy
from pathlib import Path
from unittest.mock import Mock, call, patch
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


@pytest.mark.parametrize(
    "name,value",
    [
        ("X-Probe", "abc\r\nInjected: 1"),
        ("X-Probe", "abc\rInjected: 1"),
        ("X-Probe", "abc\nInjected: 1"),
        ("X-Probe\r\nInjected", "abc"),
        ("X-Probe\r", "abc"),
        ("X-Probe\n", "abc"),
    ],
)
def test_proxy_drops_headers_with_crlf(name, value, capsys):
    """Exercise both copy boundaries without a client rejecting CRLF first."""
    module = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "bin/browser_proxy.py")
    )
    proxy = object.__new__(module["BrowserProxy"])
    proxy.path = "/health"
    proxy.command = "GET"
    proxy.client_address = ("127.0.0.1", 12345)
    proxy.headers = {"Content-Length": "0", "X-Safe": "request", name: value}
    proxy.rfile = io.BytesIO()
    proxy.wfile = io.BytesIO()
    proxy.send_response_only = Mock()
    proxy.send_header = Mock()
    proxy.end_headers = Mock()
    proxy.send_error = Mock()
    response = Mock(status=200)
    response.getheaders.return_value = [
        ("X-Safe", "response"),
        (name, value),
        ("Set-Cookie", "one=1"),
        ("Set-Cookie", "two=2"),
    ]
    response.read.return_value = b"ok"
    upstream = Mock()
    upstream.getresponse.return_value = response
    with patch("http.client.HTTPConnection", return_value=upstream):
        proxy.forward()

    forwarded = upstream.request.call_args.kwargs["headers"]
    assert forwarded["X-Safe"] == "request"
    assert name not in forwarded
    assert call("X-Safe", "response") in proxy.send_header.call_args_list
    assert call("Set-Cookie", "one=1") in proxy.send_header.call_args_list
    assert call("Set-Cookie", "two=2") in proxy.send_header.call_args_list
    for header in proxy.send_header.call_args_list:
        assert all("\r" not in part and "\n" not in part for part in header.args)
    assert proxy.wfile.getvalue() == b"ok"
    proxy.send_error.assert_not_called()
    assert capsys.readouterr().err.splitlines() == [
        "Dropped request header containing CR/LF",
        "Dropped response header containing CR/LF",
    ]
