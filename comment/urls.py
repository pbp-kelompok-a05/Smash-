# comment/urls.py
from django.urls import path
from . import views
from comment.views import show_json

app_name = 'comment'

urlpatterns = [
    # =============================================
    # COMMENT CRUD ENDPOINTS
    # =============================================
    
    # Get comments for a post & Create new comment
    path('post/<int:post_id>/', 
         views.CommentAPIView.as_view(), 
         name='comment-list-create'),
    
    # Get, Update, Delete specific comment
    path('<int:comment_id>/', 
         views.CommentAPIView.as_view(), 
         name='comment-detail'),
    
    # Comment interactions (like, report)
    path('<int:comment_id>/<str:action>/', 
         views.CommentInteractionView.as_view(), 
         name='comment-interaction'),
    
    # =============================================
    # NESTED COMMENTS ENDPOINTS
    # =============================================
    
    # Create reply to comment
    path('<int:comment_id>/replies/', 
         views.CommentAPIView.as_view(), 
         name='comment-reply-create'),
    
    # Get replies for a comment
    path('<int:comment_id>/replies/list/', 
         views.CommentAPIView.as_view(), 
         name='comment-replies-list'),
    
    # =============================================
    # COMMENT MANAGEMENT ENDPOINTS (Superuser)
    # =============================================
    
    # Admin comment management
    path('admin/comments/', 
         views.CommentAPIView.as_view(), 
         name='admin-comment-list'),
    
    path('admin/comments/<int:comment_id>/', 
         views.CommentAPIView.as_view(), 
         name='admin-comment-detail'),
    
    # =============================================
    # USER-SPECIFIC COMMENT ENDPOINTS
    # =============================================
    
    # User's own comments
    path('user/comments/', 
         views.CommentAPIView.as_view(), 
         name='user-comment-list'),
    
    # Comments liked by user
    path('user/liked-comments/', 
         views.CommentAPIView.as_view(), 
         name='user-liked-comments'),
    path('json/', show_json, name='show_json'),
]
