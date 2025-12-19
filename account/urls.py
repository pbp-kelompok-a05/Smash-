# account/urls.py
from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path("login/", views.login_register_view, name="login_register"),
    path("register/ajax/", views.register_ajax, name="register_ajax"),
    path("login/ajax/", views.login_ajax, name="login_ajax"),
    path("logout/ajax/", views.logout_ajax, name="logout_ajax"),
]
