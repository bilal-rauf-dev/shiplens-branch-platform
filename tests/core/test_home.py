import pytest
from django.db import connection
from django.utils import translation
from django.utils.translation import gettext


@pytest.mark.django_db
@pytest.mark.parametrize("language,direction", [("en", "ltr"), ("ur", "rtl")])
def test_t_i18n_dir(client, language, direction):
    # Exercise PostgreSQL rather than allowing HTTP tests to hide a broken DB setup.
    connection.ensure_connection()
    assert connection.vendor == "postgresql"
    assert connection.pg_version // 10000 == 16

    response = client.get(f"/{language}/")

    assert response.status_code == 200
    assert f'<html lang="{language}" dir="{direction}">' in response.text
    with translation.override(language):
        assert gettext("Ujala Volunteer Network") in response.text
    assert response["Content-Language"] == language


@pytest.mark.parametrize("language", ["en", "ur"])
def test_t_i18n_root_accept_language(client, language):
    response = client.get("/", HTTP_ACCEPT_LANGUAGE=language)

    assert response.status_code == 302
    assert response.url == f"/{language}/"
