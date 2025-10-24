from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    # ==================== POST CRUD URLS ====================
    path('', views.forum_post_list, name='forum_post_list'),
    path('post/<uuid:pk>/', views.forum_post_detail, name='forum_post_detail'),
    path('post/new/', views.create_forum_post, name='create_forum_post'),
    path('post/<uuid:pk>/edit/', views.update_forum_post, name='update_forum_post'),
    path('post/<uuid:pk>/delete/', views.delete_forum_post, name='delete_forum_post'),
    
    # ==================== POST INTERACTION URLS ====================
    path('post/<uuid:pk>/like/', views.like_post, name='like_post'),
    path('post/<uuid:pk>/dislike/', views.dislike_post, name='dislike_post'),
    path('post/<uuid:pk>/pin/', views.pin_post, name='pin_post'),
    path('post/<uuid:pk>/unpin/', views.unpin_post, name='unpin_post'),
    
    # ==================== USER-SPECIFIC URLS ====================
    path('my-posts/', views.my_posts, name='my_posts'),
    path('pinned-posts/', views.my_pinned_posts, name='my_pinned_posts'),
    
    # ==================== API URLS (JSON/XML) ====================
    path('api/posts/', views.show_forum_json, name='show_forum_json'),
    path('api/posts/xml/', views.show_forum_xml, name='show_forum_xml'),
    path('api/posts/<uuid:pk>/', views.show_forum_json_by_id, name='show_forum_json_by_id'),
    path('api/posts/<uuid:pk>/xml/', views.show_forum_xml_by_id, name='show_forum_xml_by_id'),
    path('api/posts/category/<int:category_id>/', views.show_forum_json_by_category, name='show_forum_json_by_category'),
]
