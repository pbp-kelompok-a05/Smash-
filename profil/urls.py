from django.urls import path
from profil.views import show_views, show_json, edit_or_create_profile, profile_api, change_password_api
from . import views

app_name = 'profil'

urlpatterns = [
    path("", show_views, name="show_views"),
    path("<int:user_id>/", show_views, name="user_profile"),
    path('json/', show_json, name='show_json'),
    path('create-profil/', edit_or_create_profile, name='edit_or_create_profile'),
    path('api/change-password/', change_password_api, name='change_password_api'),
    path('api/profile/', profile_api, name='profile_api'),
    path('api/profile-posts/', views.profile_posts_api, name='profile_posts_api'),
    path('api/profile/<int:user_id>/', profile_api, name='profile_api_detail'),
]   
