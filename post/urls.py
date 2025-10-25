# post/urls.py
from django.urls import path
from . import views

app_name = 'post'

urlpatterns = [
    # =============================================
    # POST CRUD ENDPOINTS
    # =============================================
    
    # List semua posts & Create new post
    path('', views.PostAPIView.as_view(), name='post-list-create'),
    
    # Get, Update, Delete specific post
    path('<int:post_id>/', views.PostAPIView.as_view(), name='post-detail'),
    
    # Post interactions (like, share, report)
    path('<int:post_id>/<str:action>/', 
         views.PostInteractionView.as_view(), 
         name='post-interaction'),
    
    # =============================================
    # POST MANAGEMENT ENDPOINTS (Superuser)
    # =============================================
    
    # Admin post management (superuser only)
    path('admin/posts/', 
         views.PostAPIView.as_view(), 
         name='admin-post-list'),
    
    path('admin/posts/<int:post_id>/', 
         views.PostAPIView.as_view(), 
         name='admin-post-detail'),
    
    # =============================================
    # USER-SPECIFIC POST ENDPOINTS
    # =============================================
    
    # User's own posts
    path('user/posts/', 
         views.PostAPIView.as_view(), 
         name='user-post-list'),
    
    # Posts liked by user
    path('user/liked/', 
         views.PostAPIView.as_view(), 
         name='user-liked-posts'),
    
    # Posts bookmarked by user  
    path('user/bookmarked/', 
         views.PostAPIView.as_view(), 
         name='user-bookmarked-posts'),

    # Delete and Edit
    path('<int:post_id>/', views.PostAPIView.as_view(), name='post_detail_api'),
    path('edit/<int:post_id>/', views.edit_post_page, name='edit_post'),
]