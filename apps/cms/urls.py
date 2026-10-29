from django.urls import path

from apps.cms import services, views

urlpatterns = [
    path("app/content/", views.ContentListView.as_view(), name="content-list"),
    path("app/content/create/", views.ContentEditView.as_view(), name="content-create"),
    path(
        "app/content/<int:pk>/edit/",
        views.ContentEditView.as_view(required_action="content.update"),
        name="content-edit",
    ),
    path(
        "app/content/<int:pk>/preview/",
        views.ContentPreviewView.as_view(),
        name="content-preview",
    ),
]
urlpatterns += [
    path(
        f"app/content/<int:pk>/{operation}/",
        views.ContentTransitionView.as_view(
            operation=operation, required_action=services.ACTIONS[operation]
        ),
        name=f"content-{operation}",
    )
    for operation in services.TRANSITIONS
]
