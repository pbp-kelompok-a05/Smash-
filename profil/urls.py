from django.urls import path
from profil.views import show_views,show_json,edit_or_create_profile
from . import views

app_name = 'profil'

urlpatterns = [
    path("", show_views, name="show_views"),
    path('json/', show_json, name='show_json'),
    path('create-profil/', edit_or_create_profile, name='edit_or_create_profile'),
    # API ENDPOINTS
    # path('api/profile/', ProfileAPIView.as_view(), name='profile_api'),
    # path('api/profile/<int:user_id>/', ProfileAPIView.as_view(), name='profile_api_detail'),
]   