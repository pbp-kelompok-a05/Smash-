import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import URLValidator


class ForumPost(models.Model):
    """
    Model untuk merepresentasikan postingan/diskusi dalam forum Padel.
    Mendukung konten teks, gambar, dan embed video.
    """
    
    # Primary Key menggunakan UUID untuk keamanan dan skalabilitas
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Post ID"
    )
    
    # Relasi ke model User sebagai author
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='forum_posts',
        verbose_name="Penulis"
    )
    
    title = models.CharField(
        max_length=255,
        verbose_name="Judul Post",
        help_text="Judul untuk postingan diskusi"
    )
    
    content = models.TextField(
        verbose_name="Konten Post",
        help_text="Isi konten postingan"
    )
    
    # Field opsional untuk gambar dan video
    image = models.ImageField(
        upload_to='post_images/',
        blank=True,
        null=True,
        verbose_name="Gambar Post",
        help_text="Opsional: Unggah gambar pendukung"
    )
    
    video_link = models.URLField(
        blank=True,
        null=True,
        validators=[URLValidator()],
        verbose_name="Tautan Video",
        help_text="Opsional: Tautan video embed (YouTube/Vimeo)"
    )
    
    # Timestamps untuk pelacakan
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dibuat pada"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Diperbarui pada"
    )
    
    # Metric interaksi
    likes_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Jumlah Like"
    )
    
    dislikes_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Jumlah Dislike"
    )
    
    shares_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Jumlah Share"
    )
    
    # Status moderasi
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Dihapus?",
        help_text="Penanda soft delete untuk post"
    )

    class Meta:
        """Konfigurasi tambahan untuk model"""
        ordering = ['-created_at']
        verbose_name = "Forum Post"
        verbose_name_plural = "Forum Posts"
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['author', 'created_at']),
        ]

    def __str__(self):
        """Representasi string untuk objek Post"""
        return f"{self.title} by {self.author.username}"

    def soft_delete(self):
        """Soft delete post dengan menandai is_deleted=True"""
        self.is_deleted = True
        self.save()

    def restore(self):
        """Mengembalikan post yang terhapus"""
        self.is_deleted = False
        self.save()

    # Methods untuk manajemen interaksi
    def increment_likes(self):
        """Menambah jumlah like"""
        self.likes_count += 1
        self.save()

    def decrement_likes(self):
        """Mengurangi jumlah like (jika > 0)"""
        if self.likes_count > 0:
            self.likes_count -= 1
            self.save()

    def increment_dislikes(self):
        """Menambah jumlah dislike"""
        self.dislikes_count += 1
        self.save()

    def decrement_dislikes(self):
        """Mengurangi jumlah dislike (jika > 0)"""
        if self.dislikes_count > 0:
            self.dislikes_count -= 1
            self.save()

    def increment_shares(self):
        """Menambah jumlah share"""
        self.shares_count += 1
        self.save()

    @property
    def total_interactions(self):
        """Total semua interaksi (like + dislike + share)"""
        return self.likes_count + self.dislikes_count + self.shares_count

    @property
    def is_edited(self):
        """Cek apakah post pernah diedit"""
        return self.updated_at > self.created_at.replace(microsecond=0)