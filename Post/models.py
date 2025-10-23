import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    # Attribute untuk Category yang terdiri atas nama dan deskripsi 
    name = models.CharField(max_length=255, verbose_name="Category Name")
    description = models.TextField(max_length=255, verbose_name="Description")

    # Meta class untuk handle main behavior Category
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

    # Mendapatkan URL untuk post sesuai dengan kategori 
    def get_absolute_url(self):
        return reverse('category-posts', kwargs={'pk': self.pk})


class ForumPost(models.Model):
    # List category
    POST_CATEGORY = [
        ("discussion", "Discussion"),
        ("question", "Question"),
        ("review", "Review"),
        ("nostalgia", "Nostalgia"),
    ]

    # Fields utama
    # ID khusus post -> Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Post Title
    title = models.CharField(max_length=255, verbose_name="Post Title")
    # Content Post
    content = models.TextField(verbose_name="Content")
    # Author Post -> handle untuk delete dan update POST
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts", null=True)
    # Category Post
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Post Category")
    # Post Type
    post_type = models.CharField(
        max_length=100,
        choices=POST_CATEGORY,
        default="discussion",
        verbose_name="Post Type",
    )
    
    # Media fields
    image = models.ImageField(upload_to='forum_posts/images/', null=True, blank=True, verbose_name="Post Image")
    video_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="Video URL")

    # Metadata & Status fields
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    is_pinned = models.BooleanField(default=False, verbose_name="Pinned 📌")
    is_deleted = models.BooleanField(default=False, verbose_name="Soft Deleted")
    
    # Counter fields for AJAX updates
    views = models.PositiveIntegerField(default=0, verbose_name="Views Count")
    like_count = models.PositiveIntegerField(default=0, verbose_name="Likes Count")
    dislike_count = models.PositiveIntegerField(default=0, verbose_name="Dislikes Count")
    comment_count = models.PositiveIntegerField(default=0, verbose_name="Comments Count")

    # Class Meta untuk handle main behavior ForumPost
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = "Forum Post"
        verbose_name_plural = "Forum Posts"
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['is_pinned']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author.username}"

    def clean(self):
        # Handle ketika user memasukan dua jenis media
        if self.image and self.video_url:
            raise ValidationError("Post can have either an image or a video URL, not both!")

    def get_absolute_url(self):
        # URL untuk akses ke halaman post detail
        return reverse('post-detail', kwargs={'pk': self.pk})

    # CRUD Operations
    def soft_delete(self):
        # Delete Post, tetapi bisa direstore kembali 
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])

    def restore(self):
        # Mengembalikan post yang sudah dihapus
        self.is_deleted = False
        self.save(update_fields=['is_deleted'])

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
        """Update comment count dari Comment records"""
        self.comment_count = self.comments.count()
        self.save(update_fields=['comment_count'])
        return self.comment_count

    def update_all_counts(self):
        """Update semua counters sekaligus (untuk efficiency)"""
        self.like_count = self.likes.filter(is_like=True).count()
        self.dislike_count = self.likes.filter(is_like=False).count()
        self.comment_count = self.comments.count()
        self.save(update_fields=['like_count', 'dislike_count', 'comment_count'])

    # Pin/Unpin operations
    def pin(self):
        """Pin post ke atas"""
        self.is_pinned = True
        self.save(update_fields=['is_pinned'])

    def unpin(self):
        """Unpin post"""
        self.is_pinned = False
        self.save(update_fields=['is_pinned'])

    # Utility methods
    def can_edit(self, user):
        """Cek apakah user bisa mengedit post ini"""
        return user == self.author or user.is_staff

    def can_delete(self, user):
        """Cek apakah user bisa menghapus post ini"""
        return user == self.author or user.is_staff

    @property
    def is_edited(self):
        """Cek apakah post pernah di-edit"""
        return self.updated_at > self.created_at + timezone.timedelta(seconds=60)

    @classmethod
    def get_pinned_posts(cls):
        """Mendapatkan semua pinned posts"""
        return cls.objects.filter(is_pinned=True, is_deleted=False)

    @classmethod
    def get_active_posts(cls):
        """Mendapatkan semua active posts (non-deleted)"""
        return cls.objects.filter(is_deleted=False)


class PostLike(models.Model):
    # Attribute untuk PostLike -> Mempermudah pengambilan data sehingga dipisah dari ForumPost
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_like = models.BooleanField(default=True)  # True = like, False = dislike
    created_at = models.DateTimeField(auto_now_add=True)

    # Meta Class untuk handle behavior utama PostLike
    class Meta:
        unique_together = ['post', 'user']
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
        """Override save untuk update counters"""
        super().save(*args, **kwargs)
        # Update counters di post terkait
        self.post.update_all_counts()

    def delete(self, *args, **kwargs):
        """Override delete untuk update counters"""
        post = self.post
        super().delete(*args, **kwargs)
        post.update_all_counts()