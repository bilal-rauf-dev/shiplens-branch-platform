"""The shared footer displays a translated release label only with a value."""

import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("language,label", [("en", "Version"), ("ur", "ورژن")])
@pytest.mark.parametrize("release", ["1.0.0", ""])
def test_release_footer(client, settings, language, label, release):
    settings.RELEASE_VERSION = release

    response = client.get(f"/{language}/")

    assert response.status_code == 200
    assert response.context["release_version"] == release
    footer = response.text.split("<footer", 1)[1].split("</footer>", 1)[0]
    if release:
        assert f"{label} <bdi>{release}</bdi>" in footer
    else:
        assert label not in footer
