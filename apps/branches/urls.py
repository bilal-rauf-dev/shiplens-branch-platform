from django.urls import path

from apps.branches import views

urlpatterns = [
    path("app/branches/", views.BranchListView.as_view(), name="branch-list"),
    path(
        "app/branches/create/", views.BranchCreateView.as_view(), name="branch-create"
    ),
    path(
        "app/branches/<int:pk>/", views.BranchDetailView.as_view(), name="branch-detail"
    ),
    path(
        "app/branches/<int:pk>/edit/",
        views.BranchEditView.as_view(),
        name="branch-edit",
    ),
    path("app/cities/", views.CityListView.as_view(), name="city-list"),
    path("app/cities/create/", views.CityCreateView.as_view(), name="city-create"),
    path("app/cities/<int:pk>/edit/", views.CityEditView.as_view(), name="city-edit"),
    path(
        "branches/<int:pk>/<str:action>/",
        views.branch_transition,
        name="branch-transition",
    ),
]
