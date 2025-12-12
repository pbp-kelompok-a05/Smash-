from django.urls import path
from . import views

app_name = "search"

urlpatterns = [
    path("", views.search_posts, name="search_posts"),
    path("api/", views.search_posts_api, name="search_posts_api"),
]
