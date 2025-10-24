# ads/forms.py
from django import forms
from .models import Ad

class AdForm(forms.ModelForm):
    class Meta:
        model = Ad
        fields = ['title', 'ad_type', 'image', 'link', 'active', 'start_at', 'end_at', 'popup_delay_seconds']
