from django.urls import path
from . import views

urlpatterns = [
    path("popup/", views.ads_popup, name="ads_popup"),
]
