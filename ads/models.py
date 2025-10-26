from django.db import models
from django.contrib.auth.models import User

class Advertisement(models.Model):
    """Model untuk menyimpan data iklan (CRUD hanya bisa superuser)"""
    AD_TYPE_CHOICES = [
        ('popup', 'Pop-up Ad'),
        ('inline', 'Inline Ad'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='ads/', blank=True, null=True)
    link = models.URLField(blank=True)
    ad_type = models.CharField(max_length=10, choices=AD_TYPE_CHOICES, default='inline')
    popup_delay_seconds = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_superuser': True})

    def __str__(self):
        return f"{self.title} ({self.ad_type})"

    def save(self, *args, **kwargs):
        # For inline ads, delay is irrelevant: normalize to 0
        if self.ad_type == 'inline':
            self.popup_delay_seconds = 0
        super().save(*args, **kwargs)


class PremiumSubscriber(models.Model):
    """Stores emails of users who upgraded to premium (or want ad-free)."""
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    payment_reference = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
