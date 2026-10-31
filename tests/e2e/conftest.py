"""Browser-only tests: never create or reset the target database from pytest."""

import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def remote_request_allowed(method, url, target_url):
    """Remote checks may authenticate but must not submit application actions."""
    origin, destination = urlsplit(target_url), urlsplit(url)
    login = destination.path in {"/en/accounts/login/", "/ur/accounts/login/"}
    same_origin = (destination.scheme, destination.netloc) == (
        origin.scheme,
        origin.netloc,
    )
    return method in {"GET", "HEAD", "OPTIONS"} or (
        method == "POST" and same_origin and login
    )


@pytest.fixture(scope="session", autouse=True)
def audit_test_database():
    """Override the parent DB fixture: E2E never touches a database directly."""


@pytest.fixture(scope="session")
def target_url():
    value = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise pytest.UsageError("BASE_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise pytest.UsageError("BASE_URL must not contain credentials or query data")
    return value


@pytest.fixture(scope="session")
def local_target(target_url):
    return urlsplit(target_url).hostname in LOCAL_HOSTS


@pytest.fixture(autouse=True)
def remote_read_only(request, target_url, local_target):
    """Only E2E-01 and E2E-05 may run against a remote deployment."""
    if not local_target and not request.node.get_closest_marker("read_only"):
        pytest.skip("Remote runs permit only E2E-01 and E2E-05")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, target_url, local_target):
    args = {**browser_context_args, "base_url": target_url}
    if local_target and target_url.startswith("http:"):
        # Emulate the trusted TLS proxy without weakening production settings.
        args["extra_http_headers"] = {"X-Forwarded-Proto": "https"}
    return args


@pytest.fixture(autouse=True)
def protect_remote_requests(context, target_url, local_target):
    if local_target:
        return

    def guard(route):
        request = route.request
        if remote_request_allowed(request.method, request.url, target_url):
            route.continue_()
        else:
            route.abort("blockedbyclient")

    context.route("**/*", guard)


@pytest.fixture
def login(page, target_url):
    def sign_in(role, language="en"):
        password = os.environ.get("DEMO_PASSWORD")
        if not password:
            raise pytest.UsageError("Set DEMO_PASSWORD for the seeded demo accounts")
        # Use a fresh cookie jar when moving between roles, without a logout write.
        page.context.clear_cookies()
        page.goto(f"{target_url}/{language}/accounts/login/")
        page.locator('[name="email"]').fill(f"{role}.demo@shiplens.test")
        page.locator('[name="password"]').fill(password)
        page.locator('form:has(input[name="password"]) button[type="submit"]').click()
        destination = {"hr": "hr", "branchlead": "my-branch"}.get(role, "dashboard")
        expect(page).to_have_url(f"{target_url}/{language}/app/{destination}/")

    return sign_in


@pytest.fixture
def browser_errors(page, context):
    errors = []
    context.add_init_script("""window.cspViolations = [];
        document.addEventListener('securitypolicyviolation', event => {
            window.cspViolations.push(event.violatedDirective);
        });""")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console",
        lambda event: errors.append(event.text) if event.type == "error" else None,
    )
    return errors


@pytest.fixture
def screenshot(page, output_path):
    def capture(name):
        destination = Path(output_path) / f"{name}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(destination), full_page=True)

    return capture
