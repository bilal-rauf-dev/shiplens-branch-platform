import pytest

from apps.accounts.models import Role, User


@pytest.fixture
def editor(db):
    return User.objects.create_user(
        email="editor@example.org", full_name="Content Editor", role=Role.CONTENT_EDITOR
    )


@pytest.fixture
def copy():
    return {
        "en": {
            "title": "Learning together",
            "summary": "Local learning.",
            "body_md": "## Welcome\n\nLearn **together**.",
        },
        "ur": {
            "title": "مل کر سیکھیں",
            "summary": "اپنے محلے میں سیکھیں۔",
            "body_md": "آپ ہمارے ساتھ سیکھ سکتے ہیں۔",
        },
    }
