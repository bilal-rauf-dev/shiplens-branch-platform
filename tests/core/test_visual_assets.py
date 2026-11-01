"""Bundled decorative SVGs stay local, inert and small under the strict CSP."""

import re
from pathlib import Path
from xml.etree import ElementTree

import pytest
from django.conf import settings

from apps.cms.models import ILLUSTRATIONS

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
