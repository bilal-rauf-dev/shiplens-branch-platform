"""Desktop tables fit their containers and lifted cards clear their headings."""

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("width", [1280, 1440])
def test_e2e_finance_dashboard_tables_fit(page, target_url, login, language, width):
    page.set_viewport_size({"width": width, "height": 1000})
    login("finance", language)
    page.goto(
        f"{target_url}/{language}/app/dashboard/?period=2026-10",
        wait_until="networkidle",
    )
    page.evaluate("document.fonts.ready")
    tables = page.locator(".table-container").evaluate_all("""elements => elements.map(
        element => ({
            text: element.textContent.trim(),
            scrollWidth: element.scrollWidth,
            clientWidth: element.clientWidth
        }))""")
    assert tables
    assert all(table["scrollWidth"] <= table["clientWidth"] for table in tables), tables


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_home_featured_card_heading_gap(page, target_url, language):
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(f"{target_url}/{language}/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    cards = page.locator(".section-heading + .card--featured")
    assert cards.count() > 0
    gaps = cards.evaluate_all("""elements => elements.map(element =>
        element.getBoundingClientRect().top
        - element.previousElementSibling.getBoundingClientRect().bottom)""")
    assert all(gap >= 23 for gap in gaps), gaps
