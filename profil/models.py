from django.db import models
from django.contrib.auth.models import User

def upload_to(instance, filename):
    return f"profile_photos/{instance.user.username}/{filename}"

# penambahan field untuk mengganti foto profile dan username
class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    # menambahkan blank=True agar field bio bisa kosong
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to=upload_to, null=True, blank=True)
    

