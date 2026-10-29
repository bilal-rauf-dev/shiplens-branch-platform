from django.urls import path

from apps.publicsite import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="public-about"),
    path("programs/", views.programs, name="public-programs"),
    path(
        "programs/<slug:slug>/",
        views.content_detail,
        {"type": "PROGRAM"},
        name="public-program-detail",
    ),
    path("branches/", views.branches, name="public-branches"),
    path("branches/<str:code>/", views.branch_detail, name="public-branch-detail"),
    path("events/", views.events, name="public-events"),
    path(
        "events/<slug:slug>/",
        views.content_detail,
        {"type": "EVENT"},
        name="public-event-detail",
    ),
    path("contact/", views.contact, name="public-contact"),
    path("privacy/", views.privacy, name="public-privacy"),
]
