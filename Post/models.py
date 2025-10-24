import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    """
    Model untuk kategori post forum olahraga padel.
    
    Attributes:
        name (str): Nama kategori (maks 255 karakter)
        description (str): Deskripsi kategori (maks 255 karakter)
    """
    name = models.CharField(max_length=255, verbose_name="Category Name")
    description = models.TextField(max_length=255, verbose_name="Description")

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Mendapatkan URL untuk menampilkan post berdasarkan kategori"""
        return reverse('category-posts', kwargs={'pk': self.pk})


class ForumPost(models.Model):
    """
    Model utama untuk post forum olahraga padel.
    
    Mendukung CRUD lengkap dengan fitur:
    - Create: Pengguna dapat membuat post baru dengan teks, gambar, dan video
    - Read: Semua pengguna dapat melihat daftar post dan detailnya
    - Update: Pembuat post dapat mengedit konten
    - Delete: Pembuat post dan admin dapat menghapus post (soft delete)
    
    Posts ditampilkan dalam bentuk card di halaman utama dengan:
    - Media (gambar/video)
    - Metadata (like, view, comment counts)
    - Status (pinned, deleted)
    """
    
    POST_CATEGORY = [
        ("discussion", "Discussion"),
        ("question", "Question"),
        ("review", "Review"),
        ("nostalgia", "Nostalgia"),
    ]

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Konten Utama
    title = models.CharField(max_length=255, verbose_name="Post Title")
    content = models.TextField(verbose_name="Content")
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="forum_posts", 
        null=True,
        verbose_name="Author"
    )
    
    # Kategori dan Tipe
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Post Category"
    )
    post_type = models.CharField(
        max_length=100,
        choices=POST_CATEGORY,
        default="discussion",
        verbose_name="Post Type",
    )
    
    # Media (sesuai deskripsi requirements)
    image = models.ImageField(
        upload_to='forum_posts/images/', 
        null=True, 
        blank=True, 
        verbose_name="Post Image",
        help_text="Unggah gambar untuk post Anda"
    )
    video_url = models.URLField(
        max_length=500, 
        null=True, 
        blank=True, 
        verbose_name="Video URL",
        help_text="Masukkan URL video (YouTube/Vimeo)"
    )

    # Metadata & Status
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    is_pinned = models.BooleanField(default=False, verbose_name="Pinned Post 📌")
    is_deleted = models.BooleanField(default=False, verbose_name="Soft Deleted")
    
    # Counter untuk AJAX (terintegrasi dengan model Comment)
    views = models.PositiveIntegerField(default=0, verbose_name="Views Count")
    like_count = models.PositiveIntegerField(default=0, verbose_name="Likes Count")
    dislike_count = models.PositiveIntegerField(default=0, verbose_name="Dislikes Count")
    comment_count = models.PositiveIntegerField(default=0, verbose_name="Comments Count")

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = "Forum Post"
        verbose_name_plural = "Forum Posts"
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['is_pinned']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author.username if self.author else 'Unknown'}"

    def clean(self):
        """
        Validasi custom:
        - Post tidak boleh memiliki gambar dan video URL sekaligus
        """
        if self.image and self.video_url:
            raise ValidationError("Post can have either an image or a video URL, not both!")

    def get_absolute_url(self):
        """URL untuk mengakses halaman detail post"""
        return reverse('post-detail', kwargs={'pk': self.pk})

    # === CRUD OPERATIONS ===
    def soft_delete(self):
        """
        Soft delete post - post tidak dihapus permanen
        dapat direstore kemudian
        """
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])

    def restore(self):
        """Mengembalikan post yang telah di-soft delete"""
        self.is_deleted = False
        self.save(update_fields=['is_deleted'])

    # === COUNTER MANAGEMENT ===
    def increment_views(self):
        """Menambah view count - compatible dengan AJAX"""
        self.views += 1
        self.save(update_fields=["views"])
        return self.views

    def update_like_count(self):
        """Update like count dari PostLike records"""
        self.like_count = self.likes.filter(is_like=True).count()
        self.save(update_fields=['like_count'])
        return self.like_count

    def update_dislike_count(self):
        """Update dislike count dari PostLike records"""
        self.dislike_count = self.likes.filter(is_like=False).count()
        self.save(update_fields=['dislike_count'])
        return self.dislike_count

    def update_comment_count(self):
        """Update comment count dari Comment records (terintegrasi dengan modul Comment)"""
        from Comment.models import Comment  # Import inline untuk avoid circular import
        self.comment_count = Comment.objects.filter(post=self, post__is_deleted=False).count()
        self.save(update_fields=['comment_count'])
        return self.comment_count

    def update_all_counts(self):
        """Update semua counters sekaligus untuk efisiensi"""
        from Comment.models import Comment
        
        self.like_count = self.likes.filter(is_like=True).count()
        self.dislike_count = self.likes.filter(is_like=False).count()
        self.comment_count = Comment.objects.filter(post=self, post__is_deleted=False).count()
        self.save(update_fields=['like_count', 'dislike_count', 'comment_count'])

    # === PIN/UNPIN OPERATIONS ===
    def pin(self):
        """Pin post ke atas halaman utama"""
        self.is_pinned = True
        self.save(update_fields=['is_pinned'])

    def unpin(self):
        """Unpin post dari posisi pinned"""
        self.is_pinned = False
        self.save(update_fields=['is_pinned'])

    # === PERMISSION CHECKS ===
    def can_edit(self, user):
        """
        Cek apakah user dapat mengedit post ini
        
        Returns:
            bool: True jika user adalah author atau staff
        """
        return user.is_authenticated and (user == self.author or user.is_staff)

    def can_delete(self, user):
        """
        Cek apakah user dapat menghapus post ini
        
        Returns:
            bool: True jika user adalah author atau staff
        """
        return user.is_authenticated and (user == self.author or user.is_staff)

    # === PROPERTIES ===
    @property
    def is_edited(self):
        """Cek apakah post pernah di-edit (selisih waktu > 60 detik)"""
        return self.updated_at > self.created_at + timezone.timedelta(seconds=60)

    @property
    def active_comments(self):
        """Mendapatkan comments yang terkait dengan post ini"""
        return self.comments.all()

    # === CLASS METHODS ===
    @classmethod
    def get_pinned_posts(cls):
        """Mendapatkan semua pinned posts yang tidak terhapus"""
        return cls.objects.filter(is_pinned=True, is_deleted=False)

    @classmethod
    def get_active_posts(cls):
        """Mendapatkan semua active posts (non-deleted) untuk ditampilkan"""
        return cls.objects.filter(is_deleted=False)

    @classmethod
    def get_posts_by_category(cls, category_id):
        """Mendapatkan posts berdasarkan kategori tertentu"""
        return cls.objects.filter(category_id=category_id, is_deleted=False)


class PostLike(models.Model):
    """
    Model untuk like/dislike pada post forum.
    
    Attributes:
        post (ForeignKey): Post yang dilike/dislike
        user (ForeignKey): User yang melakukan like/dislike
        is_like (bool): Status like (True) atau dislike (False)
        created_at (DateTime): Waktu pembuatan
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_like = models.BooleanField(default=True)  # True = like, False = dislike
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']  # Satu user satu like/dislike per post
        verbose_name = "Post Like"
        verbose_name_plural = "Post Likes"
        indexes = [
            models.Index(fields=['post', 'user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        action = "liked" if self.is_like else "disliked"
        return f"{self.user.username} {action} {self.post.title}"

    def save(self, *args, **kwargs):
        """Override save untuk update counters di post terkait"""
        super().save(*args, **kwargs)
        self.post.update_all_counts()

    def delete(self, *args, **kwargs):
        """Override delete untuk update counters di post terkait"""
        post = self.post
        super().delete(*args, **kwargs)
        post.update_all_counts()