from django.urls import path
from . import views

urlpatterns = [
    path("post/<uuid:post_id>/comments/", views.show_comments, name="show_comments"),
]
