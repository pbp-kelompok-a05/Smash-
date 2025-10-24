# post/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

class Post(models.Model):
    """
    MODEL: Post
    MODUL: Post 📩
    DEVELOPER: Christna
    
    DESKRIPSI: 
    Model untuk merepresentasikan postingan/forum diskusi tentang olahraga padel.
    Mendukung input teks, gambar, dan tautan video yang ditampilkan dalam bentuk card.
    
    FUNGSI UTAMA:
    - Menyimpan data postingan pengguna
    - Mengelola media (gambar/video)
    - Menangani interaksi like/dislike
    - Mendukung CRUD operations
    
    CRUD OPERATIONS:
    - Create: Pengguna menulis post baru
    - Read: Menampilkan post di homepage
    - Update: Pengguna mengedit post mereka
    - Delete: Pengguna/admin menghapus post
    
    RELASI EKSTERNAL:
    - User (pembuat post)
    - Comment (komentar pada post) [di app comment]
    - Report (laporan pada post) [di app report]
    """
    
    # Fields
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posts',
        verbose_name="Pembuat Post"
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name="Judul Post",
        help_text="Judul postingan (maksimal 200 karakter)"
    )
    
    content = models.TextField(
        verbose_name="Konten Post",
        help_text="Konten utama postingan"
    )
    
    image = models.ImageField(
        upload_to='post_images/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Gambar",
        help_text="Upload gambar (opsional)"
    )
    
    video_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Tautan Video",
        help_text="Tautan video YouTube/Vimeo (opsional)"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dibuat Pada"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Diupdate Pada"
    )
    
    likes = models.ManyToManyField(
        User,
        related_name='post_likes',
        blank=True,
        verbose_name="Like"
    )
    
    dislikes = models.ManyToManyField(
        User,
        related_name='post_dislikes',
        blank=True,
        verbose_name="Dislike"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif",
        help_text="Post aktif/tidak (untuk soft delete)"
    )

    class Meta:
        """Konfigurasi metadata untuk model Post"""
        db_table = 'post_posts'
        ordering = ['-created_at']
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['is_active']),
        ]

    def clean(self):
        """
        VALIDASI CUSTOM:
        - Hanya boleh mengisi image ATAU video_url, tidak boleh keduanya
        - Memastikan konsistensi data sebelum disimpan
        """
        super().clean()
        if self.image and self.video_url:
            raise ValidationError({
                'image': 'Hanya boleh mengisi salah satu: gambar atau tautan video.',
                'video_url': 'Hanya boleh mengisi salah satu: gambar atau tautan video.'
            })

    def save(self, *args, **kwargs):
        """Override save method untuk menjalankan validasi custom"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Representasi string untuk Post"""
        return f"Post: {self.title} by {self.user.username}"

    def get_absolute_url(self):
        """URL untuk mengakses detail post"""
        return reverse('post:post-detail', kwargs={'pk': self.pk})

    # Properties untuk analytics
    @property
    def total_likes(self):
        """Menghitung total like pada post"""
        return self.likes.count()

    @property
    def total_dislikes(self):
        """Menghitung total dislike pada post"""
        return self.dislikes.count()

    @property
    def total_comments(self):
        """Menghitung total komentar pada post"""
        # Ini akan bekerja jika ada relasi dari Comment model
        return self.comments.count() if hasattr(self, 'comments') else 0

    @property
    def has_media(self):
        """Cek apakah post memiliki media (gambar atau video)"""
        return bool(self.image or self.video_url)

    @property
    def media_type(self):
        """Mendapatkan jenis media post"""
        if self.image:
            return 'image'
        elif self.video_url:
            return 'video'
        return 'text'

    # Method untuk business logic
    def user_has_liked(self, user):
        """Cek apakah user tertentu sudah like post ini"""
        return self.likes.filter(id=user.id).exists() if user.is_authenticated else False

    def user_has_disliked(self, user):
        """Cek apakah user tertentu sudah dislike post ini"""
        return self.dislikes.filter(id=user.id).exists() if user.is_authenticated else False

    def soft_delete(self):
        """Soft delete post (menonaktifkan tanpa menghapus dari database)"""
        self.is_active = False
        self.save()

    def restore(self):
        """Mengaktifkan kembali post yang di-soft delete"""
        self.is_active = True
        self.save()

    def get_preview_content(self, length=150):
        """Mendapatkan preview konten untuk card display"""
        if len(self.content) <= length:
            return self.content
        return self.content[:length] + '...'