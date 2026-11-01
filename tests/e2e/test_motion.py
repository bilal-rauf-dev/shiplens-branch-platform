"""Local visual behavior respects reduced motion while keeping text readable."""

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("preference", ["reduce", "no-preference"])
def test_e2e_motion_preferences(page, target_url, language, preference):
    page.emulate_media(reduced_motion=preference)
    page.goto(f"{target_url}/{language}/", wait_until="domcontentloaded")
    heading = page.locator(".home-hero h1")
    expect(heading).to_be_visible()
    assert heading.evaluate("element => getComputedStyle(element).opacity") == "1"
    assert (
        heading.evaluate("element => getComputedStyle(element).animationName") == "none"
    )
    # Public pages have no script to delay DOMContentLoaded for stylesheets.
    # Wait for CSS itself before reading the final animation policy.
    expect(page.locator(".home-hero > img")).to_have_css(
        "animation-name", "none" if preference == "reduce" else "hero-arrive"
    )
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    assert heading.evaluate("""element => {
        for (; element; element = element.parentElement) {
            const style = getComputedStyle(element);
            if (style.opacity !== '1' || style.animationName !== 'none') return false;
        }
        return true;
    }""")
    card = page.locator(".public-card").first
    arrow = card.locator(".icon--arrow_forward")
    expect(arrow).to_be_visible()
    card.scroll_into_view_if_needed()

    # Normalize parent scaling so we measure the arrow's own four CSS pixels.
    def position():
        return arrow.evaluate("""element => {
            const card = element.closest('.public-card');
            const rect = card.getBoundingClientRect();
            const scale = rect.width / card.offsetWidth;
            return (element.getBoundingClientRect().x - rect.x) / scale;
        }""")

    before = position()
    card.hover()
    if preference == "reduce":
        expect(card).to_have_css("transform", "none")
        expect(arrow).to_have_css("transform", "none")
        assert position() == pytest.approx(before, abs=0.2)
    else:
        expect(arrow).to_have_css("transform", "matrix(1, 0, 0, 1, 4, 0)")
        assert position() - before == pytest.approx(
            4 if language == "en" else -4, abs=0.3
        )
    expect(arrow).to_have_css("scale", "none" if language == "en" else "-1 1")


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_staff_surfaces_stay_static(page, target_url, login, language):
    login("finance", language)
    page.goto(f"{target_url}/{language}/app/dashboard/?period=2026-10")
    chips = page.locator(".dashboard-kpis .kpi-icon")
    assert chips.count() == page.locator(".dashboard-kpis article").count()
    expect(chips.first).to_have_css("background-color", "rgb(232, 222, 248)")
    expected_scale = "none" if language == "en" else "-1 1"
    expect(page.locator(".icon--logout").first).to_have_css("scale", expected_scale)
    assert (
        page.locator('[data-status="SUBMITTED"]').first.evaluate(
            "element => getComputedStyle(element, '::before').scale"
        )
        == expected_scale
    )
    assert (
        page.locator("#money-chart").evaluate(
            "canvas => Chart.getChart(canvas).options.animation"
        )
        is False
    )
    page.goto(f"{target_url}/{language}/app/collections/")
    row = page.locator("tbody tr").first
    row.hover()
    expect(row).to_have_css("transform", "none")
    assert page.evaluate("""() => [...document.querySelectorAll(
        '.hero, .section--primary, .empty-state')].every(element =>
        ['::before', '::after'].every(pseudo =>
            ['none', 'normal'].includes(getComputedStyle(element, pseudo).content)))""")
