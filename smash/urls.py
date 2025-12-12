"""
URL configuration for smash project.
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from post import views as post_views
from smash.views import proxy_image

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("account.urls")),
    path("ads/", include("ads.urls")),
    path("post/", include("post.urls")),
    path("search/", include("search.urls")),
    path("notifications/", include("notifications.urls")),
    path("comments/", include("comment.urls")),
    path("report/", include("report.urls")),
    path("profil/", include("profil.urls")),
    path("", include("main.urls")),
    # Routing Sidebar
    path("hot/", post_views.hot_threads, name="hot_threads"),
    path("bookmark/", post_views.bookmarked_threads, name="bookmarked_threads"),
    path("recent/", post_views.recent_thread, name="recent_thread"),
    path("authentication/", include("authentication.urls")),
    path("proxy-image/", proxy_image, name="proxy_image"),
]

# Serve media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
else:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    ]
