from django.urls import path
from . import views

app_name = 'post'

urlpatterns = [
    # Basic CRUD URLs
    path('', views.PostListView.as_view(), name='post-list'),
    path('create/', views.PostCreateView.as_view(), name='post-create'),
    path('<uuid:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('<uuid:pk>/update/', views.PostUpdateView.as_view(), name='post-update'),
    path('<uuid:pk>/delete/', views.PostDeleteView.as_view(), name='post-delete'),
    
    # AJAX Interaction URLs
    path('<uuid:pk>/like/', views.LikePostView.as_view(), name='post-like'),
    path('<uuid:pk>/dislike/', views.DislikePostView.as_view(), name='post-dislike'),
    path('<uuid:pk>/share/', views.SharePostView.as_view(), name='post-share'),
    path('<uuid:pk>/stats/', views.GetPostStatsView.as_view(), name='post-stats'),
    
    # Special Pages
    path('popular/', views.PopularPostsView.as_view(), name='popular-posts'),
]