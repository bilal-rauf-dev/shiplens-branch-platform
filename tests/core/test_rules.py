import pytest
from django.test import override_settings

from apps.core import rules

pytestmark = pytest.mark.django_db


def test_t_config_defaults():
    assert rules.get("collection_lock_days") == 7
    assert rules.get("allow_submit_current_week") is False


def test_t_config_settings_override():
    with override_settings(BUSINESS_RULES={"collection_lock_days": 3}):
        assert rules.get("collection_lock_days") == 3


def test_t_config_unknown_name():
    with pytest.raises(KeyError):
        rules.get("unknown_rule")
