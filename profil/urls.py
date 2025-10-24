from django.urls import path
from profil.views import show_views,show_json,create_profil

urlpatterns = [
    path("", show_views, name="show_views"),
    path('json/', show_json, name='show_json'),
    path('create-profil/', create_profil, name='create_profil'),
]