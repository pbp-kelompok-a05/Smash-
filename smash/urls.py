"""
URL configuration for smash project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.views.generic import RedirectView
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from post import views as post_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("account.urls")),  # ← PASTIKAN PATH SPESIFIK
    path("ads/", include("ads.urls")),  # ← PASTIKAN PATH SPESIFIK
    path("post/", include("post.urls")),  # ← GUNAKAN PATH SPESIFIK
    path("comments/", include("comment.urls")),
    path("report/", include("report.urls")),
    path("profil/", include("profil.urls")),
    path("", include("main.urls")),  # ← BIARKAN MAIN MENANGANI ROOT
    # Routing Sidebar
    path("hot/", post_views.hot_threads, name="hot_threads"),
    path("bookmark/", post_views.bookmarked_threads, name="bookmarked_threads"),
    path("recent/", post_views.recent_thread, name="recent_thread"),
]

# Serve media files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files (works in both development and production)
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.BASE_DIR / "static"
    )
else:
    # In production, serve static files from STATIC_ROOT
    urlpatterns += [
        re_path(
            r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}
        ),
    ]
