# ads/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Ad(models.Model):
    TYPE_CHOICES = (
        ('popup', 'Popup'),
        ('inline', 'Inline'),
    )
    title = models.CharField(max_length=120, blank=True)
    ad_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='inline')
    image = models.ImageField(upload_to='ads/')
    link = models.URLField(blank=True, null=True)
    active = models.BooleanField(default=True)
    start_at = models.DateTimeField(blank=True, null=True)
    end_at = models.DateTimeField(blank=True, null=True)
    popup_delay_seconds = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_active_now(self):
        if not self.active:
            return False
        now = timezone.now()
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True

    def __str__(self):
        return f"{self.title or self.id} ({self.ad_type})"
