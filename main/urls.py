# main/urls.py
from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.show_main, name="show_main"),
    path('login/', views.login_user, name='login'),
    path('register/', views.register, name='register'),
]