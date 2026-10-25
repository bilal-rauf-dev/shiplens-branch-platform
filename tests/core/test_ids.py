import pytest
from django.db import transaction

from apps.core.ids import next_value
from apps.core.models import IdSequence


@pytest.mark.django_db(transaction=True)
def test_sequence_requires_callers_transaction():
    with pytest.raises(AssertionError, match="transaction.atomic"):
        next_value("branch:KHI")
    assert not IdSequence.objects.exists()


@pytest.mark.django_db
def test_sequence_rollback_and_independent_keys():
    with transaction.atomic():
        assert next_value("branch:KHI") == 1
        assert next_value("branch:LHE") == 1
    with pytest.raises(ValueError), transaction.atomic():
        assert next_value("branch:KHI") == 2
        raise ValueError("Cancel the write")
    with transaction.atomic():
        assert next_value("branch:KHI") == 2
