from django.urls import path
from . import views

urlpatterns = [
    # Halaman gabungan login + register
    path("", views.login_register_view, name="login_register"),

    # Endpoint AJAX untuk autentikasi
    path("register/", views.register_ajax, name="register_ajax"),
    path("login/", views.login_ajax, name="login_ajax"),
    path("logout/", views.logout_ajax, name="logout_ajax"),
]