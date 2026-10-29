import csv
from decimal import Decimal

from django.db.models import QuerySet
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import render
from django.utils import translation
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.accounts.permissions import require
from apps.core import clock
from apps.exports import selectors, services
from apps.exports.registry import EXPORTS


class Echo:
    def write(self, value):
        return value


def cell(value):
    """Keep money machine-readable; neutralize formula prefixes on text only."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return str(value)


def filename(code, user, params, kind):
    ids = selectors.branch_ids(user)
    scope = "all"
    if ids is not None:
        from apps.branches.models import Branch

        codes = list(Branch.objects.filter(pk__in=ids).values_list("code", flat=True))
        scope = codes[0] if len(codes) == 1 else "assigned"
    period = params.get("period") or params.get("date_from") or params.get("week_from")
    period = period.strftime("%Y-%m") if period else "all"
    generated = clock.now().astimezone(clock.KARACHI).strftime("%Y%m%dT%H%M")
    return f"shiplens_{code}_{scope}_{period}_{generated}.{kind}"


def csv_chunks(spec, rows, lang):
    # Streaming happens after middleware unwinds, so keep the chosen locale explicit.
    with translation.override(lang):
        writer = csv.writer(Echo(), lineterminator="\r\n")
        yield b"\xef\xbb\xbf"
        yield writer.writerow([str(header) for header, getter in spec.columns]).encode(
            "utf-8"
        )
        for row in (
            rows.iterator(chunk_size=500) if isinstance(rows, QuerySet) else rows
        ):
            yield writer.writerow(
                [cell(getter(row)) for header, getter in spec.columns]
            ).encode("utf-8")


@cache_control(no_store=True, private=True)
@require_GET
def export_csv(request, code):
    spec = EXPORTS.get(code)
    if spec is None:
        raise Http404
    require(request.user, spec.action)
    if services.rate_limited(request):
        return render(request, "429.html", status=429)
    form = spec.form_fn(request.user, request.GET)
    if not form.is_valid():
        return render(request, "exports/invalid.html", {"form": form}, status=400)
    lang = request.GET.get("lang", request.LANGUAGE_CODE)
    lang = lang if lang in {"en", "ur"} else request.LANGUAGE_CODE
    with translation.override(lang):
        rows = spec.rows_fn(request.user, form.cleaned_data)
        count = rows.count() if isinstance(rows, QuerySet) else len(rows)
        services.record_export(
            request.user, spec.action, code, form.cleaned_data, count, lang
        )
    response = StreamingHttpResponse(
        csv_chunks(spec, rows, lang), content_type="text/csv; charset=utf-8"
    )
    name = filename(code, request.user, form.cleaned_data, "csv")
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response
