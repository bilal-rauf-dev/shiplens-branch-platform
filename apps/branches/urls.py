from django.urls import path

from apps.branches import views

urlpatterns = [
    path(
        "branches/<int:pk>/<str:action>/",
        views.branch_transition,
        name="branch-transition",
    ),
]
