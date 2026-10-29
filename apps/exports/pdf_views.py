from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import translation
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.accounts.permissions import require, scope_queryset
from apps.core import clock, rules
from apps.dashboard import selectors as dashboard_selectors
from apps.exports import selectors, services
from apps.exports.pdf import render_pdf
from apps.exports.views import filename
from apps.finance import report_selectors


def language(request):
    selected = request.GET.get("lang", request.LANGUAGE_CODE)
    return selected if selected in {"en", "ur"} else request.LANGUAGE_CODE


def common_context(request, lang):
    return {
        "lang": lang,
        "generated_at": clock.now(),
        "generated_by": request.user,
        "demo": settings.DEMO_MODE,
    }


def response_pdf(content, name):
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response


@cache_control(no_store=True, private=True)
@require_GET
def weekly_report(request, pk):
    action = "report.export_pdf"
    require(request.user, action)
    report = get_object_or_404(
        scope_queryset(request.user, action, report_selectors.reports()), pk=pk
    )
    if services.rate_limited(request):
        return render(request, "429.html", status=429)
    lang = language(request)
    with translation.override(lang):
        details = report_selectors.detail_data(request.user, report)
        context = {**common_context(request, lang), **details, "report": report}
        content = render_pdf("pdf/weekly_report.html", context)
        services.record_export(
            request.user,
            action,
            "report",
            {"report": pk},
            len(details["lines"]),
            lang,
            kind="pdf",
        )
    name = filename("report", request.user, {"week_from": report.week_start}, "pdf")
    return response_pdf(content, name)


@cache_control(no_store=True, private=True)
@require_GET
def monthly_summary(request):
    action = "summary.export_pdf"
    require(request.user, action)
    if services.rate_limited(request):
        return render(request, "429.html", status=429)
    form = selectors.period_form(request.user, request.GET)
    if not form.is_valid():
        return render(request, "exports/invalid.html", {"form": form}, status=400)
    lang = language(request)
    with translation.override(lang):
        selected = form.cleaned_data["period"]
        as_of = clock.now()
        data = dashboard_selectors.dashboard_data(
            (selected.year, selected.month), as_of, head_office=True
        )
        count = (
            len(data["branch_rows"])
            + len(data["money_trend"])
            + len(data["unsent_rows"])
        )
        if count > rules.get("export_summary_max_rows"):
            return render(request, "exports/too_large.html", status=400)
        context = {**common_context(request, lang), **data, "period": selected}
        content = render_pdf("pdf/monthly_summary.html", context)
        services.record_export(
            request.user, action, "summary", form.cleaned_data, count, lang, kind="pdf"
        )
    return response_pdf(
        content, filename("summary", request.user, form.cleaned_data, "pdf")
    )
