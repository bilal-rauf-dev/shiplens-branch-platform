"""Page routes include a language prefix; the health probe does not."""

from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

from apps.core.views import HomeView, health

handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"

urlpatterns = [path("health", health, name="health")]
urlpatterns += i18n_patterns(
    path("", HomeView.as_view(), name="home"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.branches.urls")),
    prefix_default_language=True,
)
