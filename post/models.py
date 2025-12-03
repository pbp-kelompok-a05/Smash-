# post/models.py
from django.db import models
import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Post(models.Model):
    """
    Model untuk menyimpan data post/diskusi Padel.
    Mendukung CRUD lengkap dan akses superuser.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pembuat Post",
        related_name="posts",
    )
    title = models.CharField(max_length=255, verbose_name="Judul Post")
    content = models.TextField(
        verbose_name="Konten Lengkap", help_text="Diskusi tentang Padel"
    )
    image = models.ImageField(
        upload_to="post_images/", null=True, blank=True, verbose_name="Gambar Post"
    )
    video_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Tautan Video",
        help_text="URL video platform eksternal",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Dibuat")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Waktu Diperbarui")
    is_deleted = models.BooleanField(default=False, verbose_name="Terhapus?")

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ["-created_at"]
        permissions = [
            ("manage_all_posts", "Can manage all posts"),  # Hak akses superuser
        ]

    def __str__(self):
        return f"{self.title} oleh {self.user.username}"

    def clean(self):
        """Validasi custom: Post harus memiliki gambar atau video"""
        # Note: This validation is optional - posts can be text-only
        # Uncomment the lines below if you want to enforce image/video requirement
        # if not self.image and not self.video_link:
        #     raise ValidationError("Post harus memiliki gambar atau tautan video.")
        pass

    def delete(self, *args, **kwargs):
        """Soft delete untuk menjaga integritas data"""
        self.is_deleted = True
        self.save()

    def restore(self):
        """Memulihkan post yang terhapus"""
        self.is_deleted = False
        self.save()

    @property
    def likes_count(self):
        """Get total likes count"""
        return self.interactions.filter(interaction_type="like").count()

    @property
    def dislikes_count(self):
        """Get total dislikes count"""
        return self.interactions.filter(interaction_type="dislike").count()

    @property
    def shares_count(self):
        """Get total shares count"""
        return self.shares.count()


class PostInteraction(models.Model):
    """
    Model untuk menyimpan interaksi user dengan post (like/dislike).
    """

    INTERACTION_CHOICES = [
        ("like", "Like"),
        ("dislike", "Dislike"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pengguna",
        related_name="post_interactions",
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, verbose_name="Post", related_name="interactions"
    )
    interaction_type = models.CharField(
        max_length=10, choices=INTERACTION_CHOICES, verbose_name="Jenis Interaksi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Dibuat")

    class Meta:
        verbose_name = "Interaksi Post"
        verbose_name_plural = "Interaksi Post"
        unique_together = [
            "user",
            "post",
        ]  # User can only have one interaction per post

    def __str__(self):
        return f"{self.user.username} - {self.interaction_type} - Post #{self.post.id}"


class PostSave(models.Model):
    """
    Model untuk menyimpan post yang di-bookmark/save oleh user.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pengguna",
        related_name="saved_posts",
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, verbose_name="Post", related_name="saves"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Disimpan")

    class Meta:
        verbose_name = "Post Tersimpan"
        verbose_name_plural = "Posts Tersimpan"
        unique_together = ["user", "post"]  # User can only save a post once

    def __str__(self):
        return f"{self.user.username} saved Post #{self.post.id}"


class PostShare(models.Model):
    """
    Model untuk menyimpan data share post.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pengguna",
        related_name="shared_posts",
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, verbose_name="Post", related_name="shares"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Waktu Dibagikan")

    class Meta:
        verbose_name = "Post Share"
        verbose_name_plural = "Post Shares"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} shared Post #{self.post.id}"
