import uuid
from django.db import models


# Create your models here.
class Categoy(models.Model):
    # Define attribute yang dibutuhkan
    name = models.CharField(max_length=255, verbose_name="Category Name")
    description = models.TextField(max_length=255, verbose_name="Description")


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
    author = models.CharField(
        max_length=100,
        choices=post_kategory,
        default="category",
        verbose_name="Post Category",
    )
    # Timestamp untuk pembuatan dan update post
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    update_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    # Additions
    is_pinned = models.BooleanField(default=False, verbose_name="Pinned 📌")
    views = models.PositiveIntegerField(default=0, verbose_name="Views Count")
    likes = models.PositiveIntegerField(default=0, verbose_name="Likes Count")
    dislikes = models.PositiveIntegerField(default=0, verbose_name="Dislikes Count")

    # Method tambahan
    # Return Post title
    def __str__(self):
        return self.title

    # Increment views
    def increment_views(self):
        self.views += 1
        self.save()

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

    # Get number of comments
    def get_comment_count(self):
        return self.comments.count()

    # Pin post
    def pin(self):
        self.is_pinned = True
        self.save()

    # Unpin post
    def unpin(self):
        self.is_pinned = False
        self.save()
