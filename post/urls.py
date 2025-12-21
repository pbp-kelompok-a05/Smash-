# post/urls.py
from django.urls import path
from . import views
from search import views as search_views
from notifications import views as notifications_views

app_name = "post"

urlpatterns = [
    # =========================================================================
    # API ENDPOINTS
    # =========================================================================
    # CRUD Operations untuk Post
    path("api/posts/", views.PostAPIView.as_view(), name="post_api"),
    path(
        "api/posts/<int:post_id>/", views.PostAPIView.as_view(), name="post_api_detail"
    ),
    # Get Comments API (placed before generic action route to avoid matching collisions)
    path("api/posts/<int:post_id>/comments/", views.get_comments, name="get_comments"),
    # Post Interactions (Like, Dislike, Report, Share)
    path(
        "api/posts/<int:post_id>/<str:action>/",
        views.PostInteractionView.as_view(),
        name="post_interaction",
    ),
    # =========================================================================
    # HTML RENDERED PAGES
    # =========================================================================
    # Halaman Pencarian
    path("search/", search_views.search_posts, name="search_posts"),
    # Halaman Edit Post
    path("edit/<int:post_id>/", views.edit_post_page, name="edit_post_page"),
    # Halaman Thread Populer
    path("hot-threads/", views.hot_threads, name="hot_threads"),
    # Halaman Bookmark (Login Required)
    path("bookmarks/", views.bookmarked_threads, name="bookmarked_threads"),
    # Halaman Thread Terbaru
    path("recent-threads/", views.recent_thread, name="recent_threads"),
    # Halaman Detail Post
    path("<int:post_id>/", views.post_detail, name="post_detail"),
    # Notifications
    path(
        "notifications/", notifications_views.notifications_view, name="notifications"
    ),
    path(
        "api/notifications/",
        notifications_views.notifications_api,
        name="notifications_api",
    ),
    # Search API
    path("api/search/", search_views.search_posts_api, name="search_posts_api"),
    # Edit post
    path("edit/<int:post_id>/", views.edit_post, name="edit_post"),
    # Image Proxy
    path("image-proxy/", views.proxy_image, name="image_proxy"),
    # Create Post API
    path("api/create-post/", views.create_post_flutter, name="create_post_api"),
    # Edit Post API for Flutter clients (accepts POST with base64 image)
    path(
        "edit-flutter/<int:post_id>/", views.edit_post_flutter, name="edit_post_flutter"
    ),
    # Create Comment API
    path(
        "api/create-comment/", views.create_comment_flutter, name="create_comment_api"
    ),
]
