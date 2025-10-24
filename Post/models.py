# post/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Post(models.Model):
    """
    Model untuk menyimpan data post/diskusi Padel.
    Mendukung CRUD lengkap dan akses superuser.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pembuat Post",
        related_name="posts"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Judul Post"
    )
    content = models.TextField(
        verbose_name="Konten Lengkap",
        help_text="Diskusi tentang Padel"
    )
    image = models.ImageField(
        upload_to='post_images/',
        null=True,
        blank=True,
        verbose_name="Gambar Post"
    )
    video_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Tautan Video",
        help_text="URL video platform eksternal"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Waktu Dibuat"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Waktu Diperbarui"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Terhapus?"
    )

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['-created_at']
        permissions = [
            ("manage_all_posts", "Can manage all posts"),  # Hak akses superuser
        ]

    def __str__(self):
        return f"{self.title} oleh {self.user.username}"

    def clean(self):
        """Validasi custom: Post harus memiliki gambar atau video"""
        if not self.image and not self.video_link:
            raise ValidationError("Post harus memiliki gambar atau tautan video.")

    def delete(self, *args, **kwargs):
        """Soft delete untuk menjaga integritas data"""
        self.is_deleted = True
        self.save()

    def restore(self):
        """Memulihkan post yang terhapus"""
        self.is_deleted = False
        self.save()