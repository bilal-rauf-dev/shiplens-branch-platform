"""Rate-limit and audit exports before returning any generated content."""

from django.db import transaction
from django.db.models import Model
from django_ratelimit.core import is_ratelimited

from apps import audit
from apps.accounts.permissions import require
from apps.core import rules
from apps.core.models import IdSequence


def user_key(group, request):
    return str(request.user.pk)


def rate_limited(request):
    """Serialize DatabaseCache increments for one user's shared export budget."""
    with transaction.atomic():
        key = f"export:rate-limit:{request.user.pk}"
        IdSequence.objects.get_or_create(key=key)
        IdSequence.objects.select_for_update().get(pk=key)
        return is_ratelimited(
            request,
            group="exports",
            key=user_key,
            rate=f"{rules.get('export_rate_per_hour')}/h",
            method="GET",
            increment=True,
        )


def record_export(user, action, code, filters, row_count, lang, *, kind="csv"):
    """Record delivery metadata in the request's audit context and transaction."""
    require(user, action)
    codes = {
        "collections": "X1",
        "unsent": "X2",
        "reports": "X3",
        "report": "X4",
        "summary": "X5",
        "members": "X6",
        "audit": "X7",
    }
    filters = {
        key: value.pk if isinstance(value, Model) else value
        for key, value in filters.items()
    }
    with transaction.atomic():
        audit.record(
            user,
            f"export.{kind}",
            metadata={
                "export_code": codes[code],
                "filters": filters,
                "row_count": row_count,
                "lang": lang,
            },
        )
