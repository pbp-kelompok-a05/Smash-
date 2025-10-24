# comment/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Comment(models.Model):
    """
    Model untuk menyimpan komentar pada post Padel.
    Mendukung nested comments dan akses superuser.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pengguna",
        related_name="comments"
    )
    post = models.ForeignKey(
        'post.Post',
        on_delete=models.CASCADE,
        verbose_name="Post Terkait",
        related_name="comments"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Komentar Induk",
        related_name="replies"
    )
    content = models.TextField(
        max_length=1000,
        verbose_name="Isi Komentar"
    )
    emoji = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Reaksi Emoji"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Waktu Dibuat"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Waktu Diperbarui"
    )
    likes_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Jumlah Like"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Terhapus?"
    )

    class Meta:
        verbose_name = "Komentar"
        verbose_name_plural = "Komentar"
        ordering = ['-likes_count', '-created_at']
        permissions = [
            ("manage_all_comments", "Can manage all comments"),  # Hak akses superuser
        ]

    def __str__(self):
        return f"Komentar oleh {self.user.username} pada {self.post.title}"

    @property
    def is_reply(self):
        """Cek apakah komentar adalah balasan"""
        return self.parent is not None

    def delete(self, *args, **kwargs):
        """Soft delete dengan pelestarian thread"""
        self.is_deleted = True
        self.save()