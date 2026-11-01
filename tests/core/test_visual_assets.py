"""Bundled decorative SVGs stay local, inert and small under the strict CSP."""

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
