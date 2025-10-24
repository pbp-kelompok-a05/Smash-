# ads/forms.py
from django import forms
from .models import Advertisement

class AdForm(forms.ModelForm):
    class Meta:
        model = Advertisement
        fields = ['title', 'ad_type', 'image', 'link', 'is_active', 'start_at', 'end_at', 'delay']
