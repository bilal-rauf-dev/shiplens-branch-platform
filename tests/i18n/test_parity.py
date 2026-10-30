"""Catalogue completeness and placeholder integrity are release requirements."""

import re
import runpy
import shutil
from collections import Counter
from pathlib import Path
from string import Formatter

import polib

ROOT = Path(__file__).resolve().parents[2]
CHECKER = runpy.run_path(str(ROOT / "bin/check_translations.py"))
PERCENT_PLACEHOLDER = re.compile(
    r"%(?:\([^)]+\))?[#0\- +]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[diouxXeEfFgGcrsa%]"
)


def placeholders(text):
    """Check occurrences too, so a repeated argument cannot disappear."""
    percent = [item for item in PERCENT_PLACEHOLDER.findall(text) if item != "%%"]
    braces = [
        (name, spec, conversion)
        for _, name, spec, conversion in Formatter().parse(text)
        if name is not None
    ]
    return Counter(percent), Counter(braces)


def test_t_i18n_parity():
    catalogue = polib.pofile(ROOT / "locale/ur/LC_MESSAGES/django.po")
    assert catalogue and catalogue.percent_translated() == 100
    assert not catalogue.fuzzy_entries()
    assert not catalogue.obsolete_entries()
    for entry in catalogue:
        source = placeholders(entry.msgid)
        if entry.msgid_plural:
            assert placeholders(entry.msgid_plural) == source, entry.msgid
            assert set(entry.msgstr_plural) == {0, 1}, entry.msgid
            translations = entry.msgstr_plural.values()
        else:
            translations = [entry.msgstr]
        for translated in translations:
            assert placeholders(translated) == source, entry.msgid
            assert re.findall(r"</?[^>]+>", translated) == re.findall(
                r"</?[^>]+>", entry.msgid
            ), entry.msgid


def test_missing_message_check_includes_context_and_plural():
    committed = polib.POFile()
    committed.append(
        polib.POEntry(msgid="Returned", msgctxt="report status", msgstr="translated")
    )
    fresh = polib.POFile()
    fresh.extend(
        [
            polib.POEntry(msgid="Returned", msgctxt="report status"),
            polib.POEntry(msgid="Returned", msgctxt="parcel status"),
            polib.POEntry(msgid="%(count)s row", msgid_plural="%(count)s rows"),
        ]
    )
    assert CHECKER["missing_messages"](committed, fresh) == {
        ("parcel status", "Returned", ""),
        (None, "%(count)s row", "%(count)s rows"),
    }


def test_fresh_extraction_detects_new_code_message(tmp_path, capsys):
    for name in ("apps", "config", "templates", "formats", "locale"):
        shutil.copytree(
            ROOT / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.mo"),
        )
    shutil.copy2(ROOT / "manage.py", tmp_path / "manage.py")
    (tmp_path / "apps/core/translation_probe.py").write_text(
        "from django.utils.translation import gettext\n"
        'label = gettext("New message missing from the Urdu catalogue")\n',
        encoding="utf-8",
    )
    assert not CHECKER["check_translations"](tmp_path)
    assert "New message missing from the Urdu catalogue" in capsys.readouterr().out
