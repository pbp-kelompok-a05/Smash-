from django.utils import timezone
from django.db import models
from .models import Advertisement
import random

def ads_context(request):
    now = timezone.now()

    ads = Advertisement.objects.filter(active=True).filter(
        models.Q(start_at__lte=now) | models.Q(start_at__isnull=True),
        models.Q(end_at__gte=now) | models.Q(end_at__isnull=True),
    )

    popup_ad = ads.filter(ad_type='popup').order_by('?').first()
    inline_ad = ads.filter(ad_type='inline').order_by('?').first()


    return {
        'popup_ad': popup_ad,
        'inline_ad': inline_ad,
    }
