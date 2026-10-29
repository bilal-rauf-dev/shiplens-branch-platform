"""Exercise production asset post-processing, including referenced-file checks."""

import json
from io import StringIO

from django.core.management import call_command


def test_collectstatic_with_production_storage(settings, tmp_path):
    settings.STATIC_ROOT = tmp_path
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }

    call_command("collectstatic", interactive=False, verbosity=0, stdout=StringIO())

    manifest = json.loads((tmp_path / "staticfiles.json").read_text(encoding="utf-8"))
    assert (tmp_path / manifest["paths"]["vendor/chart.umd.min.js"]).is_file()
