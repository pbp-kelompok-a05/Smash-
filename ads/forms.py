from django import forms
from .models import Advertisement

class AdForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Required fields
        self.fields['title'].required = True
        self.fields['link'].required = True
        self.fields['ad_type'].required = True
        # popup delay only required for popup ads
        ad_type_val = None
        # Prefer posted data, then instance
        if hasattr(self, 'data') and self.data:
            ad_type_val = self.data.get('ad_type')
        if not ad_type_val and getattr(self.instance, 'pk', None):
            ad_type_val = getattr(self.instance, 'ad_type', None)

        self.fields['popup_delay_seconds'].required = (ad_type_val == 'popup')
        # Image required on create; optional on edit if already exists
        self.fields['image'].required = True
        if getattr(self.instance, 'pk', None) and getattr(self.instance, 'image', None):
            self.fields['image'].required = False
        # Description optional
        self.fields['description'].required = False

    def clean(self):
        cleaned = super().clean()
        ad_type = cleaned.get('ad_type')
        delay = cleaned.get('popup_delay_seconds')
        if ad_type == 'popup':
            # ensure delay present and non-negative
            if delay is None:
                self.add_error('popup_delay_seconds', 'This field is required for popup ads.')
            else:
                try:
                    if int(delay) < 0:
                        self.add_error('popup_delay_seconds', 'Delay must be 0 or greater.')
                except (TypeError, ValueError):
                    self.add_error('popup_delay_seconds', 'Enter a valid number.')
        else:
            # inline: normalize delay to 0 if missing
            if delay in (None, ''):
                cleaned['popup_delay_seconds'] = 0
        return cleaned
    class Meta:
        model = Advertisement
        fields = ['title', 'description', 'image', 'link', 'ad_type', 'popup_delay_seconds', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'border p-2 rounded-md w-full'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'border p-2 rounded-md w-full'}),
            'link': forms.URLInput(attrs={'class': 'border p-2 rounded-md w-full'}),
            'popup_delay_seconds': forms.NumberInput(attrs={'class': 'border p-2 rounded-md w-full'}),
        }


class PremiumSubscribeForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'border p-2 rounded-md w-full',
        'placeholder': 'Email address',
        'required': True,
    }))
