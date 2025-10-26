# post/urls.py
from django.urls import path
from . import views

app_name = 'post'

urlpatterns = [
    # =========================================================================
    # API ENDPOINTS
    # =========================================================================
    
    # CRUD Operations untuk Post
    path('api/posts/', views.PostAPIView.as_view(), name='post_api'),
    path('api/posts/<int:post_id>/', views.PostAPIView.as_view(), name='post_api_detail'),
    
    # Post Interactions (Like, Dislike, Report, Share)
    path('api/posts/<int:post_id>/<str:action>/', views.PostInteractionView.as_view(), name='post_interaction'),
    
    # =========================================================================
    # HTML RENDERED PAGES
    # =========================================================================
    
    # Halaman Pencarian
    path('search/', views.search_posts, name='search_posts'),
    
    # Halaman Thread Populer
    path('hot-threads/', views.hot_threads, name='hot_threads'),
    
    # Halaman Bookmark (Login Required)
    path('bookmarks/', views.bookmarked_threads, name='bookmarked_threads'),
    
    # Halaman Thread Terbaru
    path('recent-threads/', views.recent_thread, name='recent_threads'),
]