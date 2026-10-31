"""Local Chromium verification against a running production image.

Set BROWSER_URL, BROWSER_EMAIL and BROWSER_PASSWORD, then run this file directly
or select it with pytest -m visual. No credentials are stored in the repository.
"""

import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.visual


@pytest.mark.parametrize("language", ["en", "ur"])
def test_csp_in_chromium(language):
    url = os.environ.get("BROWSER_URL")
    if not url:
        pytest.skip("BROWSER_URL must point to a local production image")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        try:
            context = browser.new_context(
                extra_http_headers={"X-Forwarded-Proto": "https"},
                accept_downloads=True,
            )
            context.add_init_script("""window.cspViolations = [];
                document.addEventListener('securitypolicyviolation', event => {
                    window.cspViolations.push(event.violatedDirective);
                });""")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "console",
                lambda event: (
                    errors.append(event.text) if event.type == "error" else None
                ),
            )
            page.goto(f"{url}/{language}/accounts/login/")
            page.locator('[name="email"]').fill(os.environ["BROWSER_EMAIL"])
            page.locator('[name="password"]').fill(os.environ["BROWSER_PASSWORD"])
            page.locator(
                'form:has(input[name="password"]) button[type="submit"]'
            ).click()
            page.wait_for_url(f"**/{language}/app/dashboard/")
            page.wait_for_function("""() =>
                ['money-chart', 'member-chart'].every(id => {
                const chart = Chart.getChart(id);
                return chart && chart.width > 0 && chart.data.datasets.length > 0;
            })""")
            assert page.evaluate("window.cspViolations") == []
            pdf = page.locator('a[href*="/exports/summary.pdf"]')
            with page.expect_download() as pending:
                pdf.click()
            download = pending.value
            assert Path(download.path()).read_bytes().startswith(b"%PDF")
            assert page.evaluate("window.cspViolations") == []
            page.goto(f"{url}/{language}/app/content/create/", wait_until="networkidle")
            assert page.locator("form.cms-editor").is_visible()
            assert page.evaluate("window.cspViolations") == []
            assert errors == []
            print(
                f"{language}: two charts, CMS editor and PDF; zero CSP/console errors"
            )
        finally:
            browser.close()


def test_public_transfer_bytes():
    url = os.environ.get("BROWSER_URL")
    if not url:
        pytest.skip("BROWSER_URL must point to a local production image")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        try:
            page = browser.new_page(extra_http_headers={"X-Forwarded-Proto": "https"})
            session = page.context.new_cdp_session(page)
            session.send("Network.enable")
            session.send("Network.setCacheDisabled", {"cacheDisabled": True})
            types = {}
            transferred = {}
            session.on(
                "Network.responseReceived",
                lambda event: types.update({event["requestId"]: event["type"]}),
            )
            session.on(
                "Network.loadingFinished",
                lambda event: transferred.update(
                    {event["requestId"]: event["encodedDataLength"]}
                ),
            )
            response = page.goto(f"{url}/en/", wait_until="networkidle")
            assert response.status == 200
            page.evaluate("document.fonts.ready.then(() => true)")
            assert page.locator("script").count() == 0
            totals = {
                kind: int(
                    sum(
                        size
                        for key, size in transferred.items()
                        if types.get(key) == kind
                    )
                )
                for kind in ("Document", "Stylesheet", "Font", "Image")
            }
            assert totals["Document"] > 0 and totals["Stylesheet"] > 0
            result = {
                "page": "/en/",
                "bytes": totals,
                "html_css_fonts": sum(
                    totals[k] for k in ("Document", "Stylesheet", "Font")
                ),
                "total_including_images": sum(totals.values()),
                "scripts": 0,
            }
            print(json.dumps(result))
        finally:
            browser.close()


if __name__ == "__main__":
    for locale in ("en", "ur"):
        test_csp_in_chromium(locale)
    test_public_transfer_bytes()
