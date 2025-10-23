from django.urls import path
from . import views

urlpatterns = [
    path("post/<uuid:post_id>/comments/", views.show_comments, name="show_comments"),
    path(
        "post/<uuid:post_id>/comments/add/", views.add_comment, name="add_comment"
    )
]
