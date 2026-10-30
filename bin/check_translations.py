"""Compare a fresh gettext extraction with the committed Urdu message IDs."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = Path("locale/ur/LC_MESSAGES/django.po")


def message_keys(catalogue):
    """Contexts and plural source text are part of a message's identity."""
    return {
        (entry.msgctxt, entry.msgid, entry.msgid_plural)
        for entry in catalogue
        if not entry.obsolete
    }


def missing_messages(committed, fresh):
    return message_keys(fresh) - message_keys(committed)


def check_translations(root):
    """Extract in an isolated source copy; never rewrite the committed catalogue."""
    if shutil.which("xgettext") is None:
        raise SystemExit("Install GNU gettext before checking translation coverage.")
    committed = polib.pofile(root / CATALOGUE)
    with tempfile.TemporaryDirectory(prefix="shiplens-i18n-") as directory:
        copied = Path(directory)
        # Only these folders contain application Python, template or format sources.
        # Excluding tests, environments and local data also avoids copying secrets.
        for name in ("apps", "config", "templates", "formats", "locale"):
            source = root / name
            if source.exists():
                shutil.copytree(
                    source,
                    copied / name,
                    ignore=shutil.ignore_patterns("__pycache__", "*.mo"),
                )
        shutil.copy2(root / "manage.py", copied / "manage.py")
        # Extraction needs no Django settings, database connection or secrets.
        environment = os.environ.copy()
        environment.pop("DJANGO_SETTINGS_MODULE", None)
        # Fixed executable and arguments; no shell or user-supplied command.
        subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "django",
                "makemessages",
                "-l",
                "ur",
                "-e",
                "html,txt,py",
                "--no-obsolete",
            ],
            cwd=copied,
            check=True,
            env=environment,
        )
        missing = missing_messages(committed, polib.pofile(copied / CATALOGUE))
    for context, message, plural in sorted(missing, key=repr):
        print(
            f"Missing Urdu msgid: {message!r} (context={context!r}, plural={plural!r})"
        )
    if not missing:
        print(f"Urdu message coverage passed: {len(message_keys(committed))} entries.")
    return not missing


if __name__ == "__main__":
    raise SystemExit(0 if check_translations(ROOT) else 1)
