"""Night-city layers and loaders preserve accessibility, CSP and real form data."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_journeys import ur

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_night_city_layers(page, target_url, browser_errors, language):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(f"{target_url}/{language}/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    hero = page.locator(".home-hero")
    heading = hero.locator("h1")
    expect(heading).to_have_css("animation-name", "none")
    before = hero.bounding_box()["y"]
    sheet_before = page.locator(".home-sheet").bounding_box()["y"]
    page.evaluate("scrollTo(0, 400)")
    page.wait_for_function("scrollY === 400")
    assert hero.bounding_box()["y"] == pytest.approx(before, abs=1)
    bar_bottom = page.locator(".top-app-bar").evaluate(
        "element => element.getBoundingClientRect().bottom"
    )
    assert hero.bounding_box()["y"] == pytest.approx(bar_bottom, abs=1)
    sheet = page.locator(".home-sheet")
    assert sheet.bounding_box()["y"] == pytest.approx(sheet_before - 400, abs=1)
    assert sheet.evaluate("""element => {
        const box = element.getBoundingClientRect();
        const front = document.elementFromPoint(innerWidth / 2, box.top + 10);
        return element.contains(front);
    }""")
    expect(heading).to_have_css("animation-name", "none")
    assert page.evaluate("window.cspViolations") == []
    assert browser_errors == []


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_night_city_reduced_motion(page, target_url, language):
    page.emulate_media(reduced_motion="reduce")
    page.goto(f"{target_url}/{language}/", wait_until="networkidle")
    skyline = page.locator(".home-hero .skyline")
    expect(skyline).to_be_visible()
    expect(skyline).to_have_css("animation-name", "none")
    windows = page.locator(".skyline__win")
    assert windows.count() > 0
    assert windows.evaluate_all("""elements => elements.every(element =>
        getComputedStyle(element).animationName === 'none'
        && Number(getComputedStyle(element).opacity) > 0)""")
    expect(page.locator(".home-hero h1")).to_have_css("animation-name", "none")


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_submit_loader_keeps_button_data(page, target_url, language):
    page.goto(f"{target_url}/{language}/accounts/login/", wait_until="networkidle")
    page.locator('[name="email"]').fill("loader@example.test")
    page.locator('[name="password"]').fill("loader-test-password")
    form = page.locator('form:has(input[name="password"])')
    button = form.locator('button[type="submit"]')
    button.evaluate("element => { element.name = 'intent'; element.value = 'login'; }")
    name = button.inner_text()
    form.evaluate("""form => form.addEventListener('submit', event =>
        event.preventDefault(), {capture: true})""")
    button.click()
    expect(button).to_have_attribute("aria-busy", "true")
    expect(button.locator(".spinner")).to_have_count(1)
    expect(button).to_be_enabled()
    assert button.inner_text() == name
    assert button.get_attribute("name") == "intent"
    assert button.get_attribute("value") == "login"
    assert (
        form.evaluate(
            "form => new FormData(form, form.querySelector('button')).get('intent')"
        )
        == "login"
    )
    form.evaluate("form => form.requestSubmit(form.querySelector('button'))")
    expect(button.locator(".spinner")).to_have_count(1)


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_chart_loaders_finish(page, target_url, login, language):
    login("finance", language)
    page.goto(f"{target_url}/{language}/app/dashboard/?period=2026-10")
    page.wait_for_function("""() => {
        const canvases = [...document.querySelectorAll('canvas')];
        return canvases.length > 0 && canvases.every(canvas => Chart.getChart(canvas));
    }""")
    expect(page.locator(".chart-frame > .spinner")).to_have_count(0)


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_night_city_mobile_menu(page, target_url, language):
    page.set_viewport_size({"width": 360, "height": 900})
    page.goto(f"{target_url}/{language}/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator(".public-menu summary").click()
    label = "Get involved" if language == "en" else ur("Get involved")
    expect(
        page.locator(".public-menu").get_by_role("link", name=label, exact=True)
    ).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
