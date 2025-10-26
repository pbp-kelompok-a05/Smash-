from django.urls import path
from .views import (
    AdvertisementAPI,
    manage_ads_page,
    redirect_ad,
    premium_page,
    premium_checkout,
    premium_success,
)

urlpatterns = [
    path('manage/', manage_ads_page, name='manage_ads'),
    path('api/', AdvertisementAPI.as_view(), name='ad_list'),
    path('api/<int:ad_id>/', AdvertisementAPI.as_view(), name='ad_detail'),
    path('api/<int:ad_id>/update/', AdvertisementAPI.as_view(), name='ad_update'),  # TAMBAH INI!
    path('r/<int:ad_id>/', redirect_ad, name='ad_redirect'),
    path('premium/', premium_page, name='ads_premium'),
    path('premium/checkout/', premium_checkout, name='ads_premium_checkout'),
    path('premium/success/', premium_success, name='ads_premium_success'),
]
