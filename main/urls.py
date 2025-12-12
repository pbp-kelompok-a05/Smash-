# main/urls.py
from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about_smash, name="about_smash"),
    path("json/", views.json_posts, name="json_posts"),
    path("json/post/<str:post_id>/", views.json_post_id, name="json_post_detail"),
    path("json/comments/<str:post_id>/", views.json_post_comments, name="json_ads"),
    path("create_flutter_post/", views.create_post_flutter, name="create_flutter_post"),
]
