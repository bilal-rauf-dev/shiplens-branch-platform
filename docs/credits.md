# Credits

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

| Name                 | Version | License                                                                                                                                        |
|----------------------|---------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Django               | 5.2.18  | BSD-3-Clause                                                                                                                                   |
| Markdown             | 3.11.2  | BSD-3-Clause                                                                                                                                   |
| PyYAML               | 6.0.3   | MIT License                                                                                                                                    |
| argon2-cffi          | 25.1.0  | MIT                                                                                                                                            |
| argon2-cffi-bindings | 26.1.0  | MIT                                                                                                                                            |
| asgiref              | 3.13.0  | BSD-3-Clause                                                                                                                                   |
| brotli               | 1.2.1   | MIT                                                                                                                                            |
| cffi                 | 2.1.1   | MIT-0                                                                                                                                          |
| cssselect2           | 0.10.1  | BSD License                                                                                                                                    |
| dj-database-url      | 3.1.2   | BSD-3-Clause                                                                                                                                   |
| django-axes          | 8.3.1   | MIT License                                                                                                                                    |
| django-csp           | 4.0     | BSD License                                                                                                                                    |
| django-ratelimit     | 4.1.0   | Apache Software License                                                                                                                        |
| et_xmlfile           | 2.0.0   | MIT License                                                                                                                                    |
| fonttools            | 4.67.0  | MIT                                                                                                                                            |
| gunicorn             | 26.2.0  | MIT                                                                                                                                            |
| nh3                  | 0.3.7   | MIT                                                                                                                                            |
| openpyxl             | 3.1.5   | MIT License                                                                                                                                    |
| packaging            | 26.3    | Apache-2.0 OR BSD-2-Clause                                                                                                                     |
| pillow               | 13.0.0  | MIT-CMU                                                                                                                                        |
| psycopg              | 3.3.6   | LGPL-3.0-only                                                                                                                                  |
| psycopg-binary       | 3.3.6   | LGPL-3.0-only                                                                                                                                  |
| pycparser            | 3.12    | BSD-3-Clause                                                                                                                                   |
| pydyf                | 0.13.0  | BSD License                                                                                                                                    |
| pyphen               | 0.18.1  | GNU General Public License v2 or later (GPLv2+); GNU Lesser General Public License v2 or later (LGPLv2+); Mozilla Public License 1.1 (MPL 1.1) |
| sqlparse             | 0.6.0   | BSD License                                                                                                                                    |
| tinycss2             | 1.5.1   | BSD License                                                                                                                                    |
| tinyhtml5            | 2.1.0   | MIT License                                                                                                                                    |
| typing_extensions    | 4.16.0  | PSF-2.0                                                                                                                                        |
| tzdata               | 2026.5  | Apache-2.0                                                                                                                                     |
| weasyprint           | 70.0    | BSD License                                                                                                                                    |
| webencodings         | 0.6.1   | BSD License                                                                                                                                    |
| whitenoise           | 6.12.0  | MIT                                                                                                                                            |
| zopfli               | 0.4.3   | Apache Software License                                                                                                                        |

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

The four original CMS illustrations (learning, community, care and growth)
remain available for stored content. The owner-supplied unDraw illustrations,
including the unselected health/tree variants, are by Katerina Limpitsouni and
used under the [unDraw licence](https://undraw.co/license). Their geometry is
unchanged; SVG metadata is stripped, inline styles use presentation attributes,
and the original purple accent is aligned to #6750A4. The diya brand mark in
`static/img/brand/diya.svg` is original artwork authored for this project.
Public pages load no third-party fonts or
analytics. Python, PostgreSQL and the Docker image's native libraries retain their
upstream notices; the pip table inventories Python distributions, not OS packages.
Urdu PDF shaping uses Pango/HarfBuzz through WeasyPrint. Material Design 3 informed
the handwritten CSS; see [the design decision](adr/0013-material-you-css.md).
AI assistance is declared separately in the owner-maintained
[AI usage log](../AI-USAGE.md).
