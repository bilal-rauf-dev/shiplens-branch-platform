"""Page routes include a language prefix; the health probe does not."""

from django.conf.urls.i18n import i18n_patterns
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.accounts.views import set_language
from apps.core.views import health
from apps.publicsite.sitemaps import SITEMAPS
from apps.publicsite.views import robots

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", robots, name="robots"),
    path("health", health, name="health"),
    path("i18n/set-language/", set_language, name="set_language"),
]
urlpatterns += i18n_patterns(
    path("", include("apps.cms.urls")),
    path("", include("apps.exports.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.publicsite.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.branches.urls")),
    path("", include("apps.volunteers.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.finance.urls")),
    path("", include("apps.finance.report_urls")),
    prefix_default_language=True,
)
