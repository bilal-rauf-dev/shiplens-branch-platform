from django.urls import path

from apps.seed.views import reset_demo

urlpatterns = [path("app/demo/reset/", reset_demo, name="demo-reset")]
