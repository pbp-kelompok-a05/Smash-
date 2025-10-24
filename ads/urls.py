from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('manage/', views.manage_ads, name='manage_ads'),
    path('delete/<int:ad_id>/', views.delete_ad, name='delete_ad'),
    path('edit/<int:ad_id>/', views.edit_ad, name='edit_ad'),
    path('admin-login/', views.admin_login, name='admin_login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
