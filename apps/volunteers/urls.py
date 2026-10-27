from django.urls import path

from apps.volunteers import views

urlpatterns = [
    path("get-involved/", views.apply, name="volunteer-apply"),
    path("get-involved/thanks/", views.thanks, name="volunteer-thanks"),
]
