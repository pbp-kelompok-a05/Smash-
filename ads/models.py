from time import timezone
from django.db import models

# Create your models here.
class Advertisement(models.Model):
    title = models.CharField(max_length=100)
    TYPE_CHOICES = (
        ('popup', 'Popup'),
        ('inline', 'Inline'),
    )
    # Model untuk gambar iklan
    image = models.ImageField(upload_to='ads/')
    # Model untuk tipe iklan: pop-up atau inline
    ad_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    # Model untuk link iklan ketika diklik
    link = models.URLField(blank=True, null=True)
    # Model untuk delay sebelum pop-up muncul (dalam detik)
    delay = models.IntegerField(default=3)
    # Model untuk status aktif/non-aktif iklan
    is_active = models.BooleanField(default=True)
    start_at = models.DateTimeField(blank=True, null=True)
    end_at = models.DateTimeField(blank=True, null=True)
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
