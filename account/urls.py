from django.urls import path
from . import views

app_name = 'accounts' 

urlpatterns = [
    path("register/", views.register_ajax, name="register_ajax"),
    path("login/", views.login_ajax, name="login_ajax"),
    path("logout/", views.logout_ajax, name="logout_ajax"),

    path("register_page/", views.register_page_view, name="register_page"),
    
    path("", views.login_register_view, name="login_register"),
]