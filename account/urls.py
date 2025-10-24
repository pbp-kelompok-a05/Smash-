from django.urls import path
from . import views

urlpatterns = [
    # Halaman gabungan login + register (render page)
    path("", views.login_register_view, name="login_register"),

    # Buat alias /login/ yang dapat direverse sebagai 'login' (banyak library mengharapkan name 'login')
    path("login/", views.login_register_view, name="login"),

    # Endpoint AJAX untuk autentikasi (pisahkan path agar tidak bentrok dengan page)
    path("ajax/register/", views.register_ajax, name="register_ajax"),
    path("ajax/login/", views.login_ajax, name="login_ajax"),
    path("logout/", views.logout_ajax, name="logout_ajax"),
]
