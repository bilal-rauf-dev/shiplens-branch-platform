"""Generate runtime package credits from the exact lock and installed metadata."""

import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    pins = dict(
        re.findall(
            r"^([\w-]+)(?:\[[\w, -]+\])?==([^\s;\\]+)",
            (ROOT / "requirements.txt").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    for name, expected in pins.items():
        if version(name) != expected:
            raise ValueError(
                f"Install the locked version of {name} before generating credits"
            )
    # The interpreter/module are fixed; package names come from the versioned lock.
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "piplicenses",
            "--format=markdown",
            "--order=name",
            "--packages",
            *pins,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    content = (
        """# Credits

ShipLens is a solo project built with the libraries below. Django's project
scaffold is framework-generated; no website starter kit or admin theme is used.
The repository's own code is [MIT licensed](../LICENSE). Third-party components
keep their own licences and notices.

## Python runtime packages

Generated with pip-licenses 5.5.5, `--format=markdown`, from the installed versions
of every package pinned in requirements.txt (including transitive packages).
The table reports package metadata, including multiple licences where supplied.
It does not include unrelated tools installed in the authoring environment.

Regenerate in a Python 3.12 environment with both locked requirements installed:

```sh
python -m pip install --require-hashes -r requirements.txt -r requirements-dev.txt
python bin/export_credits.py
```

The script checks installed versions against the runtime lock before invoking
`python -m piplicenses --format=markdown --order=name --packages ...`.
pip-licenses is a development-only attribution tool, not an application dependency.

"""
        + result.stdout.strip()
        + """

## Vendored assets

- **Chart.js 4.6.1 — MIT:** `static/vendor/chart.umd.min.js`, dashboard only.
  [Retained licence](../static/vendor/CHARTJS-LICENSE.md).
- **Roboto — Apache-2.0:** Latin WOFF2 weights 400/500/700 in `static/fonts/`.
  [Retained licence](../static/fonts/ROBOTO-LICENSE.txt).
- **Noto Naskh Arabic — SIL Open Font License 1.1:** Urdu WOFF2 weights 400/700.
  [Retained notice](../static/fonts/NOTO-OFL.txt).
- **axe-core 4.14.0 — MPL-2.0, test-only:** `tests/e2e/vendor/axe.min.js`.
  [Licence](../tests/e2e/vendor/LICENSE),
  [third-party notices](../tests/e2e/vendor/LICENSE-3RD-PARTY.txt) and
  [provenance](../tests/e2e/vendor/README.md).

The four bundled CMS SVG illustrations are authored in this repository, rather
than fetched from an image service. Public pages load no third-party fonts or
analytics. Python, PostgreSQL and the Docker image's native libraries retain their
upstream notices; the pip table inventories Python distributions, not OS packages.
Urdu PDF shaping uses Pango/HarfBuzz through WeasyPrint. Material Design 3 informed
the handwritten CSS; see [the design decision](adr/0013-material-you-css.md).
AI assistance is declared separately in the owner-maintained
[AI usage log](../AI-USAGE.md).
"""
    )
    (ROOT / "docs" / "credits.md").write_text(content, encoding="utf-8")
    print(f"Wrote docs/credits.md for {len(pins)} locked runtime packages.")


if __name__ == "__main__":
    main()
