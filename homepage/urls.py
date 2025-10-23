from django.urls import path
from . import views

urlpatterns = [
    path("", views.homepage_view, name="homepage"),
    path("home/api/feed/", views.api_feed, name="api_feed"),
]
