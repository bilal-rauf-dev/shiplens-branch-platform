"""Guard component behaviour that can regress without changing templates."""

from pathlib import Path

import pytest
import tinycss2

CSS = Path(__file__).resolve().parents[2] / "static/css/components.css"


def rules_in(stylesheet, *, hover_media=False):
    """Walk nested CSS rules and retain whether a hover device is required."""
    for rule in stylesheet:
        if rule.type == "at-rule" and rule.content is not None:
            media = tinycss2.serialize(rule.prelude)
            children = tinycss2.parse_rule_list(rule.content)
            yield from rules_in(
                children,
                hover_media=hover_media or "(hover: hover)" in media,
            )
        elif rule.type == "qualified-rule":
            yield rule, hover_media


def test_hover_styles_only_apply_to_hover_devices():
    stylesheet = tinycss2.parse_stylesheet(CSS.read_text(encoding="utf-8"))
    for rule, hover_media in rules_in(stylesheet):
        selector = tinycss2.serialize(rule.prelude)
        if ":hover" in selector:
            assert hover_media, selector
        for declaration in tinycss2.parse_declaration_list(rule.content):
            if declaration.type == "declaration" and declaration.name == "filter":
                assert "blur(" not in tinycss2.serialize(declaration.value)


def test_decorative_shapes_fade_inside_their_boxes_and_avoid_form_cards():
    for path in CSS.parent.glob("*.css"):
        stylesheet = tinycss2.parse_stylesheet(path.read_text(encoding="utf-8"))
        for rule, _ in rules_in(stylesheet):
            selector = tinycss2.serialize(rule.prelude)
            for declaration in tinycss2.parse_declaration_list(rule.content):
                if declaration.type != "declaration":
                    continue
                value = tinycss2.serialize(declaration.value)
                if "radial-gradient(" in value:
                    assert "radial-gradient(closest-side," in value, selector
                    assert ".public-form-card" not in selector
                    assert ".login-card" not in selector
                if declaration.name == "mix-blend-mode":
                    assert selector.strip() in {".hero::before", ".hero::after"}


def test_button_state_layers_are_clipped_to_the_button():
    stylesheet = tinycss2.parse_stylesheet(CSS.read_text(encoding="utf-8"))
    for rule, _ in rules_in(stylesheet):
        if tinycss2.serialize(rule.prelude).strip() != ".btn, button":
            continue
        declarations = {
            item.name: tinycss2.serialize(item.value).strip()
            for item in tinycss2.parse_declaration_list(rule.content)
            if item.type == "declaration"
        }
        assert declarations["position"] == "relative"
        assert declarations["overflow"] == "hidden"
        assert declarations["border-radius"] == "var(--md-radius-full)"
        return
    pytest.fail("Missing shared button containment rule")


@pytest.mark.parametrize(
    "status",
    [
        "DRAFT",
        "SUBMITTED",
        "RESUBMITTED",
        "RETURNED",
        "APPROVED",
        "LOCKED",
        "FORMING",
        "ACTIVE",
        "PAUSED",
        "CLOSED",
        "OPEN",
        "SENT",
        "VOIDED",
        "PENDING",
        "ACCEPTED",
        "DECLINED",
        "INACTIVE",
        "LEFT",
    ],
)
def test_every_domain_status_has_a_colour_and_text_pair(status):
    stylesheet = tinycss2.parse_stylesheet(CSS.read_text(encoding="utf-8"))
    if status == "DRAFT":
        # The base badge already uses the secondary container for Draft.
        assert ".status-badge" in CSS.read_text(encoding="utf-8")
        return
    for rule, _ in rules_in(stylesheet):
        if f'[data-status="{status}"]' not in tinycss2.serialize(rule.prelude):
            continue
        names = {
            declaration.name
            for declaration in tinycss2.parse_declaration_list(rule.content)
            if declaration.type == "declaration"
        }
        if {"color", "background"} <= names:
            return
    pytest.fail(f"Missing readable badge colours for {status}")
