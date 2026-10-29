from django.templatetags.static import static
from django.urls import translate_url
from django.utils.translation import gettext as _

from apps.core.routes import PUBLIC_ROUTES


def public_context(request):
    match = request.resolver_match
    public = bool(match and match.url_name in PUBLIC_ROUTES)
    indexable = public and match.url_name not in {
        "account-login",
        "volunteer-thanks",
        "health",
        "set_language",
        "sitemap",
        "robots",
    }
    canonical = request.build_absolute_uri(request.path)
    descriptions = {
        "public-about": _(
            "Learn about Ujala's purpose, values and transparent offline donations."
        ),
        "public-programs": _(
            "Explore local education and food-support programs with Ujala volunteers."
        ),
        "public-branches": _(
            "Find a public Ujala branch near you and contact its local team."
        ),
        "public-events": _(
            "Discover upcoming Ujala volunteer activities and past community events."
        ),
        "volunteer-apply": _(
            "Apply to volunteer with Ujala and support your local community."
        ),
        "public-contact": _(
            "Contact the Ujala Volunteer Network head office or find a local branch."
        ),
        "public-privacy": _(
            "Read how Ujala handles private applicant and member information."
        ),
    }
    return {
        "page_title": _("Get involved")
        if match and match.url_name == "volunteer-apply"
        else _("Ujala Volunteer Network"),
        "public_page": public,
        "indexable": indexable,
        "canonical_url": canonical,
        "alternate_en": request.build_absolute_uri(translate_url(request.path, "en")),
        "alternate_ur": request.build_absolute_uri(translate_url(request.path, "ur")),
        "meta_description": descriptions.get(
            match.url_name if match else "",
            _("Light up your city with Ujala Volunteer Network."),
        ),
        "og_image": request.build_absolute_uri(static("img/cms/community.svg")),
    }
