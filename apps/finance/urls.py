from django.urls import path

from apps.finance import views

urlpatterns = [
    path("app/transfers/", views.TransferListView.as_view(), name="transfer-list"),
    path(
        "app/transfers/<int:pk>/",
        views.TransferDetailView.as_view(),
        name="transfer-detail",
    ),
    path("app/transfers/prepare/", views.prepare_transfer, name="transfer-prepare"),
    path(
        "app/branches/<int:branch_pk>/transfers/new/",
        views.TransferCreateView.as_view(),
        name="transfer-create",
    ),
    path(
        "app/collections/", views.CollectionListView.as_view(), name="collection-list"
    ),
    path(
        "app/branches/<int:branch_pk>/collections/new/",
        views.CollectionCreateView.as_view(),
        name="collection-create",
    ),
    path(
        "app/collections/<int:pk>/",
        views.CollectionDetailView.as_view(),
        name="collection-detail",
    ),
    path(
        "app/collections/<int:pk>/edit/",
        views.CollectionEditView.as_view(),
        name="collection-edit",
    ),
    path(
        "app/collections/<int:pk>/void/",
        views.CollectionVoidView.as_view(),
        name="collection-void",
    ),
]
