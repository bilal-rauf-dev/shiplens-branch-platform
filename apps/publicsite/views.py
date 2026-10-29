from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from apps.branches.selectors import public_branches
from apps.publicsite import selectors
from apps.publicsite.forms import CityFilterForm


@require_GET
def home(request):
    rows = selectors.cards(request.LANGUAGE_CODE)
    sections = {row["slug"]: row for row in rows if row["type"] == "PAGE_SECTION"}
    upcoming, _past = selectors.event_groups(
        [row for row in rows if row["type"] == "EVENT"]
    )
    return render(
        request,
        "public/home.html",
        {
            "hero": sections.get("home-hero"),
            "impact": sections.get("home-impact"),
            "programs": [row for row in rows if row["type"] == "PROGRAM"],
            "featured": upcoming[0] if upcoming else None,
            "page_title": sections.get("home-hero", {}).get(
                "title", _("Light up your city")
            ),
        },
    )


@require_GET
def about(request):
    return render(
        request,
        "public/sections.html",
        {
            "page_title": _("About us"),
            "sections": [
                row
                for row in selectors.cards(request.LANGUAGE_CODE, "PAGE_SECTION")
                if row["slug"].startswith("about-")
            ],
        },
    )


@require_GET
def programs(request):
    return render(
        request,
        "public/programs.html",
        {
            "page_title": _("Programs"),
            "programs": selectors.cards(request.LANGUAGE_CODE, "PROGRAM"),
        },
    )


@require_GET
def content_detail(request, slug, type):
    content = selectors.detail(type, slug, request.LANGUAGE_CODE)
    return render(
        request,
        "public/detail.html",
        {"content": content, "page_title": content["title"]},
    )


@require_GET
def events(request):
    upcoming, past = selectors.event_groups(
        selectors.cards(request.LANGUAGE_CODE, "EVENT")
    )
    return render(
        request,
        "public/events.html",
        {"page_title": _("Events"), "upcoming": upcoming, "past": past},
    )


@require_GET
def branches(request):
    form = CityFilterForm(request.GET)
    rows = public_branches()
    valid = form.is_valid()
    if not valid:
        rows = rows.none()
    elif form.cleaned_data.get("city"):
        rows = rows.filter(city=form.cleaned_data["city"])
    return render(
        request,
        "public/branches.html",
        {"page_title": _("Our branches"), "branches": rows, "form": form},
        status=200 if valid else 400,
    )


@require_GET
def branch_detail(request, code):
    branch = get_object_or_404(public_branches(), code=code)
    title = branch.name_ur if request.LANGUAGE_CODE == "ur" else branch.name_en
    return render(
        request, "public/branch_detail.html", {"page_title": title, "branch": branch}
    )


@require_GET
def contact(request):
    return render(request, "public/contact.html", {"page_title": _("Contact")})


@require_GET
def privacy(request):
    return render(
        request,
        "public/sections.html",
        {
            "page_title": _("Privacy notice"),
            "sections": [
                row
                for row in selectors.cards(request.LANGUAGE_CODE, "PAGE_SECTION")
                if row["slug"] == "privacy-notice"
            ],
        },
    )
