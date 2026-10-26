"""Exercise branch pages through real routes and the PostgreSQL permission scope."""

from unittest.mock import patch

import polib
import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.accounts.services import assign_branch
from apps.audit.models import AuditLog
from apps.branches import selectors, services
from apps.branches.models import Branch, BranchStatus, City

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return User.objects.create_user(
        email="screen-admin@example.com",
        full_name="Screen Admin",
        role=Role.SUPER_ADMIN,
    )


@pytest.fixture
def admin_client(client, admin):
    client.force_login(admin, backend="apps.accounts.backends.EmailBackend")
    return client


def branch_payload(city, name="Central"):
    return {
        "city": city.pk,
        "name_en": name,
        "name_ur": "مرکزی شاخ",
        "address_en": "Main Road",
        "address_ur": "مرکزی سڑک",
        "phone": "+923001234567",
        "email": "CENTRAL@EXAMPLE.COM",
    }


def make_branch(admin, city, name="Central"):
    payload = branch_payload(city, name)
    payload["city"] = city
    return services.create_branch(admin, **payload)


@pytest.mark.parametrize("role", [Role.BRANCH_LEAD, Role.HR_LEAD])
def test_t_rbac_scope_branch(admin, client, role):
    khi = City.objects.get(code="KHI")
    lhe = City.objects.get(code="LHE")
    assigned = make_branch(admin, khi, "Karachi branch")
    other = make_branch(admin, lhe, "Lahore branch")
    operator = User.objects.create_user(
        email="scoped-screen@example.com", full_name="Scoped", role=role
    )
    assign_branch(admin, operator, assigned)
    client.force_login(operator, backend="apps.accounts.backends.EmailBackend")
    listing = client.get(reverse("branch-list"))
    assert listing.status_code == 200
    assert assigned.code in listing.text
    assert other.code not in listing.text
    assert client.get(reverse("branch-detail", args=[assigned.pk])).status_code == 200
    hidden = client.get(reverse("branch-detail", args=[other.pk]))
    missing = client.get(reverse("branch-detail", args=[other.pk + 999]))
    assert hidden.status_code == missing.status_code == 404
    assert hidden.content == missing.content
    assert client.get(reverse("branch-create")).status_code == 403


def test_finance_reads_all_and_content_editor_is_denied(admin, client):
    branch = make_branch(admin, City.objects.get(code="KHI"))
    finance = User.objects.create_user(
        email="finance-screen@example.com",
        full_name="Finance",
        role=Role.FINANCE_REVIEWER,
    )
    client.force_login(finance, backend="apps.accounts.backends.EmailBackend")
    assert branch.code in client.get(reverse("branch-list")).text
    detail = client.get(reverse("branch-detail", args=[branch.pk]))
    assert detail.status_code == 200
    assert 'aria-label="History"' not in detail.text
    assert "branch-transition" not in detail.text
    editor = User.objects.create_user(
        email="editor-screen@example.com", full_name="Editor", role=Role.CONTENT_EDITOR
    )
    client.force_login(editor, backend="apps.accounts.backends.EmailBackend")
    assert client.get(reverse("branch-list")).status_code == 403
    assert client.get(reverse("branch-detail", args=[branch.pk])).status_code == 403


def test_t_pub_branch_visibility(admin):
    cities = [City.objects.get(code=code) for code in ("KHI", "LHE", "ISB", "RWP")]
    branches = [
        make_branch(admin, city, f"Branch {index}") for index, city in enumerate(cities)
    ]
    for branch, status in zip(branches, BranchStatus.values, strict=True):
        Branch.objects.filter(pk=branch.pk).update(status=status)
    public = list(selectors.public_branches())
    assert {branch.pk for branch in public} == {b.pk for b in branches[:3]}
    assert public == sorted(
        public, key=lambda branch: (branch.city.code, branch.name_en)
    )


def test_branch_create_edit_forms_keep_protected_fields_server_owned(
    admin_client, admin
):
    city = City.objects.get(code="KHI")
    create_url = reverse("branch-create")
    form_page = admin_client.get(create_url)
    assert form_page.status_code == 200
    assert 'name="status"' not in form_page.text
    assert 'name="code"' not in form_page.text
    payload = {**branch_payload(city), "status": "CLOSED", "code": "MANUAL"}
    response = admin_client.post(create_url, payload)
    branch = Branch.objects.get(name_en="Central")
    assert response.status_code == 302
    assert response.url == reverse("branch-detail", args=[branch.pk])
    assert branch.code == "BR-KHI-01" and branch.status == BranchStatus.FORMING
    assert branch.email == "central@example.com"
    edit_url = reverse("branch-edit", args=[branch.pk])
    edit_page = admin_client.get(edit_url)
    assert edit_page.status_code == 200
    assert 'name="city"' not in edit_page.text
    edited = admin_client.post(
        edit_url,
        {
            **branch_payload(city, "Renamed"),
            "code": "MANUAL",
            "status": "CLOSED",
            "city": City.objects.get(code="LHE").pk,
        },
    )
    branch.refresh_from_db()
    assert edited.status_code == 302
    assert branch.name_en == "Renamed" and branch.city_id == city.pk
    assert branch.code == "BR-KHI-01" and branch.status == BranchStatus.FORMING
    assert AuditLog.objects.filter(action="branch.created").count() == 1
    assert AuditLog.objects.filter(action="branch.updated").count() == 1


def test_branch_duplicate_name_and_bad_contact_show_form_errors(admin_client, admin):
    city = City.objects.get(code="KHI")
    make_branch(admin, city)
    duplicate = admin_client.post(reverse("branch-create"), branch_payload(city))
    assert duplicate.status_code == 200
    assert "errorlist" in duplicate.text
    invalid = admin_client.post(
        reverse("branch-create"),
        {
            **branch_payload(city, "Different"),
            "phone": "bad",
        },
    )
    assert invalid.status_code == 200
    assert "errorlist" in invalid.text
    assert Branch.objects.count() == 1


def test_city_list_create_edit_use_audited_services(admin_client):
    assert admin_client.get(reverse("city-list")).status_code == 200
    created = admin_client.post(
        reverse("city-create"),
        {
            "code": "ABC",
            "name_en": "Example",
            "name_ur": "مثال",
        },
    )
    city = City.objects.get(code="ABC")
    assert created.status_code == 302 and created.url == reverse("city-list")
    form = admin_client.get(reverse("city-edit", args=[city.pk]))
    assert 'name="code"' not in form.text
    edited = admin_client.post(
        reverse("city-edit", args=[city.pk]),
        {
            "name_en": "Changed",
            "name_ur": "تبدیل",
            "code": "XYZ",
        },
    )
    city.refresh_from_db()
    assert edited.status_code == 302
    assert city.code == "ABC" and city.name_en == "Changed"
    assert AuditLog.objects.filter(action="city.created").count() == 1
    assert AuditLog.objects.filter(action="city.updated").count() == 1
    duplicate = admin_client.post(
        reverse("city-create"),
        {
            "code": "ABC",
            "name_en": "Again",
            "name_ur": "دوبارہ",
        },
    )
    assert duplicate.status_code == 200 and "errorlist" in duplicate.text


def test_urdu_register_uses_bilingual_names_and_labels(
    admin, admin_client, settings, tmp_path
):
    source = settings.BASE_DIR / "locale" / "ur" / "LC_MESSAGES" / "django.po"
    compiled = tmp_path / "ur" / "LC_MESSAGES" / "django.mo"
    compiled.parent.mkdir(parents=True)
    polib.pofile(str(source)).save_as_mofile(str(compiled))
    settings.LOCALE_PATHS = [tmp_path]
    branch = make_branch(admin, City.objects.get(code="KHI"))
    listing = admin_client.get("/ur/app/branches/")
    assert listing.status_code == 200
    assert "شاخیں" in listing.text
    assert branch.name_ur in listing.text
    detail = admin_client.get(f"/ur/app/branches/{branch.pk}/")
    assert detail.status_code == 200
    assert "تاریخچہ" in detail.text
    assert "شاخ بنائی گئی" in detail.text


def test_city_audit_failure_rolls_back_creation_and_edit(admin):
    with patch(
        "apps.branches.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            services.create_city(admin, code="ABC", name_en="Example", name_ur="مثال")
    assert not City.objects.filter(code="ABC").exists()
    city = City.objects.get(code="KHI")
    original = city.name_en
    with patch(
        "apps.branches.services.audit.record",
        side_effect=RuntimeError("audit unavailable"),
    ):
        with pytest.raises(RuntimeError):
            services.update_city(admin, city, name_en="Changed", name_ur="بدلا")
    city.refresh_from_db()
    assert city.name_en == original


@pytest.mark.parametrize(
    "role,shows_history",
    [
        (Role.SUPER_ADMIN, True),
        (Role.FINANCE_REVIEWER, False),
        (Role.BRANCH_LEAD, True),
        (Role.HR_LEAD, True),
    ],
)
def test_history_panel_respects_entity_permission(
    admin, client, role, shows_history, clock
):
    branch = make_branch(admin, City.objects.get(code="KHI"))
    actor = (
        admin
        if role == Role.SUPER_ADMIN
        else User.objects.create_user(
            email="history-role@example.com", full_name="History Role", role=role
        )
    )
    if role in {Role.BRANCH_LEAD, Role.HR_LEAD}:
        assign_branch(admin, actor, branch)
    client.force_login(actor, backend="apps.accounts.backends.EmailBackend")
    response = client.get(reverse("branch-detail", args=[branch.pk]))
    assert response.status_code == 200
    assert ('aria-label="History"' in response.text) == shows_history
    assert ("Branch created" in response.text) == shows_history
    if shows_history:
        assert admin.email in response.text
        assert "PKT" in response.text
        assert "English name" in response.text


def test_transition_post_redirect_get_and_errors(admin_client, admin, monkeypatch):
    branch = make_branch(admin, City.objects.get(code="KHI"))
    detail_url = reverse("branch-detail", args=[branch.pk])
    activate = reverse(
        "branch-transition", kwargs={"pk": branch.pk, "action": "activate"}
    )
    success = admin_client.post(activate)
    assert success.status_code == 302 and success.url == detail_url
    detail = admin_client.get(success.url)
    assert detail.status_code == 200
    assert "Branch status updated." in detail.text
    assert 'role="status"' in detail.text
    assert "Branch status updated." not in admin_client.get(detail_url).text
    conflict = admin_client.post(activate)
    assert conflict.status_code == 409
    assert 'role="alert"' in conflict.text
    assert branch.code in conflict.text
    pause = reverse("branch-transition", kwargs={"pk": branch.pk, "action": "pause"})
    invalid = admin_client.post(pause, {"reason": "bad"})
    assert invalid.status_code == 400
    assert 'role="alert"' in invalid.text
    assert "bad</textarea>" in invalid.text
    assert admin_client.post(pause, {"reason": "Power outage"}).status_code == 302
    branch.refresh_from_db()
    assert branch.status == BranchStatus.PAUSED
    monkeypatch.setattr(services, "close_blockers", lambda row: ["Unsent collections"])
    close = reverse("branch-transition", kwargs={"pk": branch.pk, "action": "close"})
    blocked = admin_client.post(close, {"reason": "Ready to close"})
    assert blocked.status_code == 409
    assert "Unsent collections" in blocked.text
    branch.refresh_from_db()
    assert branch.status == BranchStatus.PAUSED


def test_t_growth_n_branches_list_stays_bounded(
    admin, admin_client, django_assert_max_num_queries
):
    cities = list(City.objects.order_by("code")[:10])
    made = [
        make_branch(admin, cities[index % 10], f"Branch {index:02d}")
        for index in range(50)
    ]
    assert len({branch.code for branch in made}) == 50
    with django_assert_max_num_queries(10):
        first = admin_client.get(reverse("branch-list"))
    assert first.status_code == 200
    assert first.context["page_obj"].paginator.count == 50
    assert len(first.context["branches"]) == 25
    second = admin_client.get(reverse("branch-list"), {"page": 2})
    assert second.status_code == 200
    assert len(second.context["branches"]) == 25
    filtered = admin_client.get(
        reverse("branch-list"),
        {
            "city": cities[0].pk,
            "status": BranchStatus.FORMING,
        },
    )
    assert filtered.status_code == 200
    assert filtered.context["page_obj"].paginator.count == 5
