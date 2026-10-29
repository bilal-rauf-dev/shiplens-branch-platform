import runpy
from pathlib import Path

import pytest

CHECKER = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "bin/check_conventions.py")
)


def test_logical_css_passes(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "main.css").write_text(
        "body { margin-inline: 0; padding-block: 1rem; max-inline-size: 72rem; "
        "line-height: 1.5; }"
    )

    assert CHECKER["find_violations"](tmp_path) == []


@pytest.mark.parametrize("css", ["a { margin-left: 2px; }", "a { width: 20px; }"])
def test_physical_css_reports_source_location(tmp_path, css):
    static = tmp_path / "static"
    static.mkdir()
    (static / "main.css").write_text(css)

    violations = CHECKER["find_violations"](tmp_path)

    assert len(violations) == 1
    assert "main.css:1:" in violations[0]


def test_view_writes_and_csrf_exemptions_are_rejected(tmp_path):
    app = tmp_path / "apps" / "example"
    app.mkdir(parents=True)
    (app / "views.py").write_text("obj.save()\nModel.objects.get(pk=1)\n")
    (app / "services.py").write_text("obj.save()\n")
    (app / "middleware.py").write_text("@csrf_exempt\n")

    violations = CHECKER["find_violations"](tmp_path)

    assert len(violations) == 3
    assert not any("services.py" in violation for violation in violations)


def test_only_cms_filter_may_mark_html_safe(tmp_path):
    app = tmp_path / "apps" / "cms" / "templatetags"
    app.mkdir(parents=True)
    (app / "cms.py").write_text("return mark_safe(sanitize(value))\n")
    assert CHECKER["find_violations"](tmp_path) == []
    (app / "other.py").write_text("return mark_safe(value)\n")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "bad.html").write_text("{{ value|safe }}")
    assert len(CHECKER["find_violations"](tmp_path)) == 2
