from django.urls import path

from apps.audit import views

urlpatterns = [
    path("app/audit/", views.AuditListView.as_view(), name="audit-list"),
    path("app/audit/<int:pk>/", views.AuditDetailView.as_view(), name="audit-detail"),
    path("app/audit/verify/", views.verify, name="audit-verify"),
]
