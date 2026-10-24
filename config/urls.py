"""Public routes always include the language prefix."""

from django.conf.urls.i18n import i18n_patterns
from django.urls import path

from apps.core.views import HomeView

urlpatterns = i18n_patterns(
    path("", HomeView.as_view(), name="home"),
    prefix_default_language=True,
)
