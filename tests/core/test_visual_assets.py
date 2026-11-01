"""Bundled decorative SVGs stay local, inert and small under the strict CSP."""

import re
from pathlib import Path
from xml.etree import ElementTree

import pytest
import tinycss2
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory

from apps.accounts.models import Role, User
from apps.branches.models import BranchStatus
from apps.cms.models import ILLUSTRATIONS, ContentStatus
from apps.finance.models import CollectionState, ReportStatus
from apps.volunteers.models import ApplicationStatus, MemberStatus

ROOT = Path(__file__).resolve().parents[2]
SVGS = sorted((ROOT / "static/img").rglob("*.svg"))


@pytest.mark.parametrize("path", [path for path, label in ILLUSTRATIONS if path])
def test_t_ui_illustration_choices_exist(path):
    assert (settings.BASE_DIR / "static" / path).is_file()


@pytest.mark.parametrize("path", SVGS, ids=lambda path: path.name)
def test_t_ui_svg_safety(path):
    assert path.stat().st_size <= 60_000
    # These are repository assets, never untrusted uploaded XML.
    root = ElementTree.fromstring(path.read_text(encoding="utf-8"))  # noqa: S314
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    for element in root.iter():
        assert element.tag.rsplit("}", 1)[-1].lower() not in {
            "script",
            "foreignobject",
            "style",
            "animate",
            "animatetransform",
        }
        for name, value in element.attrib.items():
            local_name = name.rsplit("}", 1)[-1].lower()
            assert not local_name.startswith("on")
            assert local_name != "style"
            if local_name == "href":
                assert value.startswith("#")


def test_t_ui_template_icon_contract():
    templates = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "templates").rglob("*.html")
    )
    used = set(re.findall(r"\bicon--([a-z0-9_]+)\b", templates))
    css = (ROOT / "static/css/icons.css").read_text(encoding="utf-8")
    declared = set(re.findall(r"\.icon--([a-z0-9_]+)\s*\{", css))
    assert used
    assert used <= declared, used - declared
    for name in declared:
        assert (ROOT / "static/img/icons" / f"{name}.svg").is_file(), name
        assert f'mask-image: url("../img/icons/{name}.svg")' in css


@pytest.mark.parametrize(
    "statuses",
    [
        BranchStatus,
        CollectionState,
        ReportStatus,
        ApplicationStatus,
        MemberStatus,
        ContentStatus,
    ],
)
def test_t_ui_every_status_has_an_explicit_mask(statuses):
    masks = set()
    css = (ROOT / "static/css/icons.css").read_text(encoding="utf-8")
    for rule in tinycss2.parse_stylesheet(
        css, skip_comments=True, skip_whitespace=True
    ):
        if rule.type != "qualified-rule":
            continue
        declarations = tinycss2.parse_declaration_list(rule.content)
        if any(
            item.type == "declaration" and item.lower_name == "mask-image"
            for item in declarations
        ):
            masks.update(
                re.findall(
                    r'\[data-status="([A-Z_]+)"\]::before',
                    tinycss2.serialize(rule.prelude),
                )
            )
    assert set(statuses.values) <= masks


@pytest.mark.parametrize("role", Role.values)
def test_t_ui_staff_navigation_icons_are_distinct(role):
    request = RequestFactory().get("/en/app/dashboard/")
    rendered = render_to_string(
        "partials/staff_navigation.html",
        {"user": User(role=role), "request": request, "csrf_token": "test-token"},
    )
    icons = re.findall(r"\bicon--([a-z0-9_]+)\b", rendered)
    assert icons
    assert len(icons) == len(set(icons)), (role, icons)


def test_t_ui_motion_is_opt_in_and_composited():
    """Future CSS must not animate layout, colour or reduced-motion pages."""
    transitions = []

    def declarations(content, opted_in, *, keyframe=False):
        for declaration in tinycss2.parse_declaration_list(
            content, skip_comments=True, skip_whitespace=True
        ):
            if declaration.type != "declaration":
                continue
            name = declaration.lower_name
            value = tinycss2.serialize(declaration.value).strip()
            if keyframe:
                assert name in {"opacity", "transform"}
            if name == "scroll-behavior":
                assert value != "smooth"
            if name.startswith(("animation", "transition")) and value != "none":
                assert opted_in, (name, value)
                if name in {"transition", "transition-property"}:
                    properties = set(re.findall(r"(?:^|,)\s*([-\w]+)", value))
                    assert properties <= {"opacity", "transform"}

    def rules(items, opted_in=False):
        for rule in items:
            if rule.type == "qualified-rule":
                declarations(rule.content, opted_in)
            elif rule.type == "at-rule" and rule.content is not None:
                if rule.lower_at_keyword == "media":
                    media = tinycss2.serialize(rule.prelude)
                    rules(
                        tinycss2.parse_rule_list(rule.content),
                        opted_in or "prefers-reduced-motion: no-preference" in media,
                    )
                elif rule.lower_at_keyword == "keyframes":
                    assert opted_in
                    for frame in tinycss2.parse_rule_list(
                        rule.content, skip_comments=True, skip_whitespace=True
                    ):
                        declarations(frame.content, opted_in, keyframe=True)
                elif rule.lower_at_keyword == "view-transition":
                    assert opted_in
                    assert "navigation: auto" in tinycss2.serialize(rule.content)
                    transitions.append(rule)

    for path in (ROOT / "static/css").glob("*.css"):
        rules(tinycss2.parse_stylesheet(path.read_text(encoding="utf-8")))
    assert len(transitions) == 1
