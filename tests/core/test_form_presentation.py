"""Form labels, hit areas and grouping share one accessible presentation."""

from html.parser import HTMLParser
from pathlib import Path

import pytest
import tinycss2

from apps.accounts.forms import ChangePasswordForm, LoginForm
from apps.accounts.models import Role, User


class FormMarkup(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.labels = []
        self.controls = {}
        self.ids = []
        self.label = None
        self.label_text = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag in {"label", "legend"}:
            self.label = attributes
            self.label_text = []
        if tag == "input" and "id" in attributes:
            self.controls[attributes["id"]] = (attributes, self.label)

    def handle_data(self, data):
        if self.label is not None:
            self.label_text.append(data)

    def handle_endtag(self, tag):
        if tag in {"label", "legend"} and self.label is not None:
            self.labels.append("".join(self.label_text))
            self.label = None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path", ["/en/get-involved/", "/ur/get-involved/", "/en/accounts/login/"]
)
def test_rendered_form_labels_have_no_colon_suffix(client, path):
    response = client.get(path)
    assert response.status_code == 200
    markup = FormMarkup(response.text)
    assert markup.labels
    for label in markup.labels:
        assert not label.split("*", 1)[0].strip().endswith(":"), label
    assert len(markup.ids) == len(set(markup.ids)), "Form IDs must be unique"
    assert 'class="required-indicator" aria-hidden="true"' in response.text
    assert 'class="visually-hidden"' in response.text


@pytest.mark.django_db
def test_public_choice_controls_belong_to_their_label_rows(client):
    response = client.get("/en/get-involved/")
    markup = FormMarkup(response.text)
    for attributes, label in markup.controls.values():
        if attributes.get("type") not in {"checkbox", "radio"}:
            continue
        assert label is not None
        assert label["class"] == "choice-row"
        assert label["for"] == attributes["id"]
    assert 'href="/en/privacy/"' in response.text
    assert 'id="id_privacy_consent_hint" tabindex="-1"' in response.text


@pytest.mark.django_db
def test_login_and_django_password_form_share_required_labels():
    user = User.objects.create_user(
        email="form-label@example.org", full_name="Form Test", role=Role.SUPER_ADMIN
    )
    for form in (LoginForm(request=None), ChangePasswordForm(user)):
        assert form.label_suffix == ""
        markup = str(form.as_p())
        assert "required-indicator" in markup
        assert all(
            not label.split("*", 1)[0].strip().endswith(":")
            for label in FormMarkup(markup).labels
        )


def test_choice_control_size_is_separate_from_the_label_hit_area():
    path = Path(__file__).resolve().parents[2] / "static/css/components.css"
    rules = tinycss2.parse_stylesheet(path.read_text(encoding="utf-8"))
    for rule in rules:
        if rule.type != "qualified-rule":
            continue
        if (
            tinycss2.serialize(rule.prelude).strip()
            != 'input[type="checkbox"], input[type="radio"]'
        ):
            continue
        declarations = {
            item.name: tinycss2.serialize(item.value).strip()
            for item in tinycss2.parse_declaration_list(rule.content)
            if item.type == "declaration"
        }
        assert declarations["inline-size"] == "1.25rem"
        assert declarations["block-size"] == "1.25rem"
        return
    pytest.fail("Missing checkbox and radio control size rule")
