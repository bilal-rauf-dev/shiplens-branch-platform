"""Exercise production asset post-processing, including referenced-file checks."""

import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client


@pytest.mark.django_db
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

    settings.WHITENOISE_AUTOREFRESH = False
    settings.WHITENOISE_USE_FINDERS = False
    client = Client()
    hashed = client.get(f"/static/{manifest['paths']['css/base.css']}")
    assert hashed.status_code == 200
    assert hashed["Cache-Control"] == "max-age=31536000, public, immutable"
    hashed.close()
    mutable = client.get("/static/css/base.css")
    assert mutable.status_code == 200
    assert "immutable" not in mutable["Cache-Control"]
    mutable.close()
