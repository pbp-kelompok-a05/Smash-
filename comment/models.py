# comment/models.py
from django.db import models
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()


class Comment(models.Model):
    """
    Model untuk menyimpan komentar pada post Padel.
    Mendukung nested comments dan akses superuser.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Pengguna", related_name="comments"
    )
    post = models.ForeignKey(
        "post.Post",
        on_delete=models.CASCADE,
        verbose_name="Post Terkait",
        related_name="comments",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Komentar Induk",
        related_name="replies",
    )
    content = models.TextField(max_length=1000, verbose_name="Isi Komentar")
    emoji = models.CharField(max_length=10, blank=True, verbose_name="Reaksi Emoji")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Dibuat")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Waktu Diperbarui")
    likes_count = models.PositiveIntegerField(default=0, verbose_name="Jumlah Like")
    dislikes_count = models.PositiveIntegerField(
        default=0, verbose_name="Jumlah Dislike"
    )
    is_deleted = models.BooleanField(default=False, verbose_name="Terhapus?")

    class Meta:
        verbose_name = "Komentar"
        verbose_name_plural = "Komentar"
        ordering = ["-likes_count", "-created_at"]
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


class CommentInteraction(models.Model):
    """
    Model untuk menyimpan interaksi user dengan comment (like/dislike).
    """

    INTERACTION_CHOICES = [
        ("like", "Like"),
        ("dislike", "Dislike"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pengguna",
        related_name="comment_interactions",
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        verbose_name="Komentar",
        related_name="interactions",
    )
    interaction_type = models.CharField(
        max_length=10, choices=INTERACTION_CHOICES, verbose_name="Jenis Interaksi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Dibuat")

    class Meta:
        verbose_name = "Interaksi Komentar"
        verbose_name_plural = "Interaksi Komentar"
        unique_together = [
            "user",
            "comment",
        ]  # User can only have one interaction per comment

    def __str__(self):
        return f"{self.user.username} - {self.interaction_type} - Comment #{self.comment.id}"
