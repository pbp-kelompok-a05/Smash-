from django.urls import path
from . import views

urlpatterns = [
    # ==================== POST CRUD ====================
    path("", views.forum_post_list, name="forum_post_list"),
    path("<uuid:post_id>/", views.forum_post_detail, name="forum_post_detail"),
    path("create/", views.create_forum_post, name="create_forum_post"),
    path("<uuid:post_id>/edit/", views.update_forum_post, name="update_forum_post"),
    path("<uuid:post_id>/delete/", views.delete_forum_post, name="delete_forum_post"),

    # ==================== USER-SPECIFIC VIEWS ====================
    path("my-posts/", views.my_posts, name="my_posts"),
    path("pinned/", views.my_pinned_posts, name="my_pinned_posts"),

    # ==================== POST INTERACTION ====================
    path("<uuid:post_id>/like/", views.like_post, name="like_post"),
    path("<uuid:post_id>/dislike/", views.dislike_post, name="dislike_post"),
    path("<uuid:post_id>/unlike/", views.unlike_post, name="unlike_post"),
    path("<uuid:post_id>/undislike/", views.undislike_post, name="undislike_post"),
    path("<uuid:post_id>/pin/", views.pin_post, name="pin_post"),
    path("<uuid:post_id>/unpin/", views.unpin_post, name="unpin_post"),

    # ==================== API VIEWS ====================
    path("api/json/", views.show_forum_json, name="show_forum_json"),
    path("api/xml/", views.show_forum_xml, name="show_forum_xml"),
    path("api/json/<uuid:post_id>/", views.show_forum_json_by_id, name="show_forum_json_by_id"),
    path("api/xml/<uuid:post_id>/", views.show_forum_xml_by_id, name="show_forum_xml_by_id"),
    path("api/json/category/<str:category>/", views.show_forum_json_by_category, name="show_forum_json_by_category"),

    # ==================== STATISTICS ====================
    path("stats/", views.forum_statistics, name="forum_statistics"),
]