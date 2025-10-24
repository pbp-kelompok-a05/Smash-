from django.db import models
from django.contrib.auth.models import User

class Profile(models.model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    bio=models.TextField()
