"""Local screenshots: pytest tests/visual -m visual --browser-channel chrome --no-cov.

The live_server fixture starts Django against the local PostgreSQL test database.
The normal test command deselects these cases, and CI always skips them.
"""

import asyncio
import os
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from playwright.async_api import async_playwright

pytestmark = [
    pytest.mark.visual,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        bool(os.environ.get("CI")), reason="Local visual checks are excluded from CI."
    ),
]


@pytest.mark.parametrize(
    "viewport",
    [
        {"width": 1440, "height": 900},
        {"width": 390, "height": 844},
    ],
    ids=["desktop", "mobile"],
)
@pytest.mark.parametrize(
    "path,name",
    [
        ("/en/", "en-home"),
        ("/ur/", "ur-home"),
        ("/en/get-involved/", "en-application"),
        ("/ur/get-involved/", "ur-application"),
        ("/en/accounts/login/", "en-login"),
        ("/en/programs/", "en-programs"),
        ("/ur/events/", "ur-events"),
        ("/en/branches/", "en-branches"),
    ],
)
def test_public_screenshot(live_server, viewport, path, name, pytestconfig):
    with override_settings(
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
    ):
        call_command(
            "import_sample_data", str(settings.BASE_DIR / "sample_data"), verbosity=0
        )
    channel = pytestconfig.getoption("--browser-channel")
    asyncio.run(capture_page(live_server.url, viewport, path, name, channel))


async def capture_page(server_url, viewport, path, name, channel):
    """Close the browser event loop before Django's synchronous database cleanup."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel=channel)
        try:
            page = await browser.new_page(viewport=viewport)
            await check_and_capture(page, server_url, viewport, path, name)
        finally:
            await browser.close()


async def check_and_capture(page, server_url, viewport, path, name):
    await page.emulate_media(reduced_motion="reduce")
    response = await page.goto(f"{server_url}{path}", wait_until="networkidle")
    assert response.status == 200
    await page.evaluate("document.fonts.ready.then(() => true)")

    if "get-involved" in path:
        consent = page.locator("#id_privacy_consent")
        assert not await consent.is_checked()
        privacy_path = "/ur/privacy/" if path.startswith("/ur/") else "/en/privacy/"
        await page.locator(f'a[href="{privacy_path}"]').first.click()
        assert page.url.endswith(privacy_path)
        await page.go_back(wait_until="networkidle")
        assert not await consent.is_checked(), (
            "Reading the notice must not toggle consent"
        )
        await page.locator('label[for="id_privacy_consent"]').click()
        assert await consent.is_checked(), "The label row must toggle its checkbox"
        await consent.uncheck()
    await page.evaluate("document.activeElement.blur(); window.scrollTo(0, 0)")
    await page.mouse.move(0, 0)
    destination = Path(__file__).resolve().parents[2] / ".tmp/screenshots"
    destination.mkdir(parents=True, exist_ok=True)
    await page.screenshot(
        path=str(destination / f"{name}-{viewport['width']}x{viewport['height']}.png"),
        full_page=True,
    )

    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
        "Horizontal overflow"
    )
    assert await page.locator("html").get_attribute("dir") == (
        "rtl" if path.startswith("/ur/") else "ltr"
    )
    if viewport["width"] < 768 and "login" not in path:
        await page.locator(".public-menu summary").click()
        assert await page.locator('header [aria-current="page"]:visible').count() == 1
        await page.locator(".public-menu summary").click()
    else:
        assert await page.locator('header [aria-current="page"]:visible').count() == 1
    assert (
        await page.locator(".brand").evaluate(
            "node => getComputedStyle(node).fontWeight"
        )
        == "500"
    )
    assert (
        await page.locator(".brand").evaluate(
            "node => getComputedStyle(node).textDecorationLine"
        )
        == "none"
    )
    if "get-involved" in path or "login" in path:
        assert (
            await page.locator(".public-form-card, .login-card").evaluate(
                "node => getComputedStyle(node, '::before').content"
            )
            == "none"
        )
    for control in await page.locator(
        'input[type="checkbox"], input[type="radio"]'
    ).all():
        dimensions = await control.evaluate("""node => {
            const box = node.getBoundingClientRect();
            const label = node.closest('label').getBoundingClientRect();
            const span = node.closest('label').querySelector('span');
            const text = span.getBoundingClientRect();
            const fontSize = getComputedStyle(document.documentElement).fontSize;
            return {width: box.width, height: box.height, target: label.height,
                expected: parseFloat(fontSize) * 1.25,
                alignment: Math.abs((box.y + box.height / 2)
                    - (text.y + text.height / 2))};
        }""")
        assert abs(dimensions["width"] - dimensions["expected"]) < 0.1
        assert abs(dimensions["height"] - dimensions["expected"]) < 0.1
        assert dimensions["target"] >= 44
        assert dimensions["alignment"] < 1
