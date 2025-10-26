from django.urls import path
from profil.views import show_views,show_json,edit_or_create_profile

app_name = 'profil'

urlpatterns = [
    path("", show_views, name="show_views"),
    path('json/', show_json, name='show_json'),
    path('create-profil/', edit_or_create_profile, name='edit_or_create_profile'),
]