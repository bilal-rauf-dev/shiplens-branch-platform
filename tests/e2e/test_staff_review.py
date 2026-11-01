"""Staff typography, export labels and table wrapping remain clear in EN/UR."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_journeys import ur

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("role", ["finance", "hr", "branchlead"])
def test_e2e_staff_hierarchy_exports_and_wrapping(
    page, target_url, login, role, language
):
    login(role, language)
    destination = {"finance": "dashboard", "hr": "hr", "branchlead": "my-branch"}[role]
    page.goto(
        f"{target_url}/{language}/app/{destination}/?period=2026-10",
        wait_until="networkidle",
    )
    sizes = page.locator("main").evaluate("""main => ({
        h1: parseFloat(getComputedStyle(main.querySelector('h1')).fontSize),
        h2: [...main.querySelectorAll('h2')].map(
            el => parseFloat(getComputedStyle(el).fontSize))
    })""")
    assert sizes["h2"] and all(size < sizes["h1"] for size in sizes["h2"])
    if role == "hr":
        return
    summary = "Export summary CSV"
    unsent = "Export unsent CSV"
    if language == "ur":
        summary, unsent = ur(summary), ur(unsent)
    expect(page.get_by_role("link", name=summary, exact=True)).to_have_count(
        1 if role == "finance" else 0
    )
    expect(page.get_by_role("link", name=unsent, exact=True)).to_have_count(1)
    if role == "finance":
        table = page.locator("table:has(td.nowrap)")
        amount = table.locator("td.numeric").first
        for width in (360, 768, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            expect(table.locator("tbody")).to_have_css(
                "display", "grid" if width < 640 else "table-row-group"
            )
            expect(amount).to_have_css("white-space", "nowrap")
            expect(table.locator("td.nowrap").first).to_have_css(
                "white-space", "nowrap"
            )
            assert (
                amount.locator("bdi").evaluate("""element => {
                const range = document.createRange(); range.selectNodeContents(element);
                const lines = [...range.getClientRects()].map(
                    rect => Math.round(rect.y));
                return new Set(lines).size;
            }""")
                == 1
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert (
                table.evaluate(
                    """element => {
                        const wrapper = element.closest('.table-container');
                        return getComputedStyle(wrapper).overflowX;
                    }"""
                )
                == "auto"
            )
    page.goto(f"{target_url}/{language}/app/collections/", wait_until="networkidle")
    label = "Export CSV" if language == "en" else ur("Export CSV")
    expect(page.get_by_role("link", name=label, exact=True)).to_have_count(1)


@pytest.mark.parametrize("language", ["en", "ur"])
def test_e2e_audit_action_chip_is_text_only(page, target_url, login, language):
    login("superadmin", language)
    page.goto(f"{target_url}/{language}/app/audit/", wait_until="networkidle")
    chip = page.locator(".status-badge:not([data-status])").first
    expect(chip).to_be_visible()
    assert (
        chip.evaluate("element => getComputedStyle(element, '::before').content")
        == "none"
    )
