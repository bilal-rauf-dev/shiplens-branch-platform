from django.urls import path

from apps.volunteers import views

urlpatterns = [
    path(
        "app/applications/",
        views.ApplicationListView.as_view(),
        name="application-list",
    ),
    path(
        "app/applications/<int:pk>/",
        views.ApplicationDetailView.as_view(),
        name="application-detail",
    ),
    path("app/applications/<int:pk>/accept/", views.accept, name="application-accept"),
    path(
        "app/applications/<int:pk>/decline/", views.decline, name="application-decline"
    ),
    path(
        "app/applications/<int:pk>/reassign/",
        views.reassign,
        name="application-reassign",
    ),
    path(
        "app/members/<int:pk>/", views.MemberDetailView.as_view(), name="member-detail"
    ),
    path("get-involved/", views.apply, name="volunteer-apply"),
    path("get-involved/thanks/", views.thanks, name="volunteer-thanks"),
]
