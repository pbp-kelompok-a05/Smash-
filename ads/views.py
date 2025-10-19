from django.shortcuts import render
from .models import Advertisement

# Create your views here.

def ads_popup(request):
    ad = Advertisement.objects.filter(is_active=True).first()
    return render(request, 'ads/popup.html', {'ad': ad})
