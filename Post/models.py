# Import library yang dibutuhkan 
# UUID digunakan untuk primary key sebuah entitas
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# Create your models here.
class Category(models.Model):
    # Define attribute yang dibutuhkan
    # Membuat nama dan deskripsi untuk kategori 
    name = models.CharField(max_length=255, verbose_name="Category Name")
    description = models.TextField(max_length=255, verbose_name="Description")

    # Handle perilaku class Category 
    # Membuat class meta untuk menyimpan metadata/opsi 
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

# Class untuk Post ke Forum
class ForumPost(models.Model):
    # Define type atau kategori post
    post_kategory = [
        ("discussion", "Discussion"),
        ("question", "Question"),
        ("review", "Review"),
        ("nostalgia", "Nostalgia"),
    ]

    # Define attribute yang dibutuhkan
    # ID post
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Judul post
    title = models.CharField(max_length=255, verbose_name="Post Title")
    # Content post -> Isi dari Post
    content = models.TextField(verbose_name="content")
    # Author atau penulis Post
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts", null=True)
    # Category untuk post 
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Post Category")
    # Kategori post
    post_type = models.CharField(
        max_length=100,
        choices=post_kategory,
        default="category",
        verbose_name="Post Category",
    )

    # Fields untuk media -> gambar dan video_url
    image = models.ImageField(upload_to='forum_posts/images/', null=True, blank=True, verbose_name="Post Image")
    video_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="Video URL")

    # Metadata untuk class ForumPost
    # Timestamp untuk pembuatan dan update post
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    update_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    # Additions
    is_pinned = models.BooleanField(default=False, verbose_name="Pinned 📌")
    # Delete pin
    is_deleted = models.BooleanField(default=False, verbose_name="Soft Deleted")

    # Counters
    views = models.PositiveIntegerField(default=0, verbose_name="Views Count")
    likes = models.PositiveIntegerField(default=0, verbose_name="Likes Count")
    dislikes = models.PositiveIntegerField(default=0, verbose_name="Dislikes Count")

    # Class Meta
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = "Forum Post"
        verbose_name_plural = "Forum Posts"

    # Method tambahan
    # Return Post title
    def __str__(self):
        return self.title

    # Handle jika user ingin mengirimkan dua media
    def clean(self):
        if self.image and self.video_url:
            raise ValidationError("Post can have either an image or a video URL, not both!")

    # Menghapus post forum
    def soft_deleted(self):
        self.is_deleted = True
        self.save()

    # User dapat mengembalikan postnya setelah dihapus
    def restore(self):
        self.is_deleted = False
        self.save()

    # Mendapatkan jumlah like dan dislike
    def get_likes_count(self):
        return self.likes.filter(is_like=True).count()

    def get_dislikes_count(self):
        return self.likes.filter(is_like=False).count()
    
    def get_comment_count(self):
        return self.comments.filter(is_deleted=False).count()

    # Increment views
    def increment_views(self):
        self.views += 1
        self.save(update_fields=["views"])

    # Like post
    def like(self):
        self.likes += 1
        self.save()

    # Dislike post
    def dislike(self):
        self.dislikes += 1
        self.save()

    # Unlike post
    def unlike(self):
        if self.likes > 0:
            self.likes -= 1
            self.save()

    # Undislike post
    def undislike(self):
        if self.dislikes > 0:
            self.dislikes -= 1
            self.save()

    # Pin post
    def pin(self):
        self.is_pinned = True
        self.save()

    # Unpin post
    def unpin(self):
        self.is_pinned = False
        self.save()

# Class unutk PostLike -> Dipisah dari Forum Post untuk mempermudah proses pengambilan data
class PostLike(models.Model):
    # Membuat attribute yang dibutuhkan 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_like = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Membuat class Meta untuk handle perilaku PostLike
    class Meta:
        unique_together = ['post', 'user']
        verbose_name = "Post Like"
        verbose_name_plural = "Post Likes"
