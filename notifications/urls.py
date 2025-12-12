from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notifications_view, name="notifications"),
    path("api/", views.notifications_api, name="notifications_api"),
]
