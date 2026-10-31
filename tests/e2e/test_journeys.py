"""The five handbook journeys run through public browser UI and real HTTP."""

import re
import time
from pathlib import Path
from uuid import uuid4

import polib
import pytest
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[2]
AXE = (Path(__file__).parent / "vendor/axe.min.js").read_text(encoding="utf-8")
PUBLIC_PAGES = (
    "",
    "about/",
    "programs/",
    "branches/",
    "events/",
    "get-involved/",
    "contact/",
    "privacy/",
)
pytestmark = pytest.mark.e2e


def ur(message):
    return polib.pofile(ROOT / "locale/ur/LC_MESSAGES/django.po").find(message).msgstr


@pytest.mark.read_only
@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_e2e_01_public_pages(page, target_url, browser_errors, language, path):
    response = page.goto(f"{target_url}/{language}/{path}", wait_until="networkidle")
    assert response.status == 200
    expect(page.locator("html")).to_have_attribute("lang", language)
    assert page.evaluate("window.cspViolations") == []
    assert browser_errors == []
    # DevTools evaluation injects the test library without relaxing the site's CSP.
    page.evaluate(AXE)
    results = page.evaluate("""async () => {
        const result = await axe.run(document);
        return result.violations.filter(item =>
            ['serious', 'critical'].includes(item.impact));
    }""")
    assert results == [], results
    assert page.evaluate("window.cspViolations") == []
    assert browser_errors == []


def test_e2e_02_application_to_member(page, target_url, login):
    suffix = uuid4().hex[:10]
    email = f"e2e-{suffix}@example.test"
    page.goto(f"{target_url}/en/get-involved/")
    rendered = time.monotonic()
    page.locator('[name="full_name"]').fill(
        "Browser Volunteer "
        + suffix.translate(str.maketrans("0123456789", "abcdefghij"))
    )
    page.locator('[name="email"]').fill(email)
    page.locator('[name="phone"]').fill("+923" + str(int(suffix, 16))[-9:].zfill(9))
    page.locator('[name="date_of_birth"]').fill("2000-01-01")
    branch = (
        page.locator('[name="preferred_branch"] option')
        .filter(has_text="BR-KHI-01")
        .get_attribute("value")
    )
    page.locator('[name="preferred_branch"]').select_option(branch)
    page.locator('[name="interests"]').first.check()
    page.locator('[name="availability"][value="weekends"]').check()
    page.locator('[name="motivation"]').fill(
        "I would like to support tutoring and community volunteering in Karachi."
    )
    page.locator('[name="preferred_language"][value="en"]').check()
    page.locator('[name="privacy_consent"]').check()
    # Exercise the real BR-051 timer; do not forge or bypass the signed token.
    time.sleep(max(0, 3.2 - (time.monotonic() - rendered)))
    page.get_by_role("button", name="Submit application", exact=True).click()
    expect(page).to_have_url(re.compile(r"/en/get-involved/thanks/\?ref=APP-"))
    reference = re.search(r"APP-\d{4}-\d+", page.locator("main").inner_text()).group()
    login("hr")
    page.goto(f"{target_url}/en/app/applications/?q={email}")
    row = page.locator("tbody tr").filter(has_text=reference)
    row.locator('a[href*="/app/applications/"]').first.click()
    form = page.locator('form[action$="/accept/"]')
    role = form.locator('[name="role_id"] option').nth(1).get_attribute("value")
    form.locator('[name="role_id"]').select_option(role)
    form.get_by_role("button", name="Confirm accept", exact=True).click()
    member = page.locator('a[href*="/app/members/"]').filter(
        has_text=re.compile(r"M-\d")
    )
    expect(member).to_be_visible()
    member_id = member.inner_text()
    page.goto(f"{target_url}/en/app/members/?q={email}")
    expect(page.locator("tbody")).to_contain_text(member_id)
    page.locator("tbody a").filter(has_text=member_id).click()
    expect(page.locator("main")).to_contain_text(email)


def test_e2e_03_urdu_usage(page, target_url, login, screenshot):
    page.goto(f"{target_url}/ur/")
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    screenshot("urdu-home")
    page.locator("header .language-switcher button").click()
    expect(page).to_have_url(f"{target_url}/en/")
    page.locator("header .language-switcher button").click()
    expect(page).to_have_url(f"{target_url}/ur/")
    page.goto(f"{target_url}/ur/get-involved/")
    # Bypass native validation only, so the real server validates an empty form.
    time.sleep(3.2)
    page.locator("main form").evaluate("form => { form.noValidate = true; }")
    page.locator('main button[type="submit"]').click()
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    expect(page.locator(".form-errors").first).to_contain_text(
        ur("This field is required.")
    )
    screenshot("urdu-form-errors")
    login("finance", "ur")
    page.goto(f"{target_url}/ur/app/collections/")
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    expect(page.locator("h1")).to_have_text(ur("Collections"))
    expect(page.locator("table")).to_be_visible()
    screenshot("urdu-collections")
    page.goto(f"{target_url}/ur/app/dashboard/?period=2026-10")
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    expect(page.locator("h1")).to_have_text(ur("Head-office dashboard"))
    expect(page.locator(".dashboard-kpis article").first).to_contain_text(
        "Rs 73,250.50"
    )
    screenshot("urdu-dashboard")


def test_e2e_04_report_cycle(page, target_url, login):
    login("branchlead")
    page.goto(f"{target_url}/en/app/collections/")
    page.locator('a[href$="/collections/new/"]').first.click()
    # The server supplies today's Karachi business date in its HTML constraints.
    date = page.locator('[name="collection_date"]')
    date.fill(date.get_attribute("max"))
    page.locator('[name="amount"]').fill("10.00")
    page.locator('[name="method"]').select_option("CASH")
    receipt = f"E2E-{uuid4().hex[:12]}"
    page.locator('[name="receipt_no"]').fill(receipt)
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.locator("main")).to_contain_text(receipt)
    collection_url = page.url
    try:
        page.goto(
            f"{target_url}/en/app/reports/?week_from=2026-10-19&week_to=2026-10-19"
        )
        row = page.locator("tbody tr").filter(has_text="BR-KHI-01")
        expect(row.locator('[data-status="DRAFT"]')).to_be_visible()
        row.locator('a[href*="/app/reports/"]').click()
        report_url = page.url
        report_id = report_url.rstrip("/").split("/")[-1]
        page.locator('[name="activities"]').fill(
            "Tutoring and community ration packing."
        )
        page.locator('[name="volunteer_hours"]').fill("56")
        page.get_by_role("button", name="Submit for review", exact=True).click()
        expect(page.locator('[data-status="SUBMITTED"]')).to_be_visible()
        login("finance")
        page.goto(report_url)
        page.locator('[name="comment"]').fill("Please clarify the tutoring activities.")
        page.get_by_role("button", name="Return to branch", exact=True).click()
        expect(page.locator('[data-status="RETURNED"]')).to_be_visible()
        login("branchlead")
        page.goto(report_url)
        expect(page.locator("main")).to_contain_text(
            "Please clarify the tutoring activities."
        )
        page.get_by_role("button", name="Resubmit", exact=True).click()
        expect(page.locator('[data-status="RESUBMITTED"]')).to_be_visible()
        login("finance")
        page.goto(report_url)
        page.get_by_role("button", name="Approve and lock", exact=True).click()
        expect(page.locator('[data-status="LOCKED"]')).to_have_text("Locked")
        login("superadmin")
        page.goto(
            f"{target_url}/en/app/audit/?entity_type=weeklyreport&entity=2026-10-19"
        )
        rows = page.locator("tbody tr").filter(
            has=page.locator(f'a[href="/en/app/reports/{report_id}/"]')
        )
        actions = rows.locator("td:nth-child(3)").all_text_contents()
        assert [action.strip() for action in actions] == [
            "report.locked",
            "report.approved",
            "report.resubmitted",
            "report.returned",
            "report.submitted",
            "report.drafted",
        ]
    finally:
        # Void through the normal UI to preserve the fixed October collected KPI.
        login("branchlead")
        page.goto(collection_url)
        page.locator('[name="reason"]').fill("Disposable browser test collection.")
        page.locator('main button[type="submit"]').click()
        expect(page.locator('[data-status="VOIDED"]')).to_be_visible()


@pytest.mark.read_only
def test_e2e_05_finance_dashboard(page, target_url, login, browser_errors):
    login("finance")
    page.goto(f"{target_url}/en/app/dashboard/?period=2026-10")
    card = page.locator(".dashboard-kpis article").filter(
        has=page.get_by_role("heading", name="Collected", exact=True)
    )
    expect(card).to_contain_text("Rs 73,250.50")
    assert page.evaluate("window.cspViolations") == []
    assert browser_errors == []
