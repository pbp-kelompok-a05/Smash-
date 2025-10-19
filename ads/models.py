from django.db import models

# Create your models here.
class Advertisement(models.Model):
    title = models.CharField(max_length=100)
    # Model untuk gambar iklan
    image = models.ImageField(upload_to='ads/')
    # Model untuk link iklan ketika diklik
    link = models.URLField(blank=True, null=True)
    # Model untuk delay sebelum pop-up muncul (dalam detik)
    delay = models.IntegerField(default=3)
    # Model untuk status aktif/non-aktif iklan
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
