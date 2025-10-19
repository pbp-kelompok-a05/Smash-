import uuid
from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Comment(models.Model):
    # Attribute untuk Comment
    post = models.ForeignKey(
        "Post.ForumPost",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Related Post",
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    content = models.TextField(verbose_name="Comment Content")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    likes = models.PositiveIntegerField(default=0, verbose_name="Likes Count")
    dislikes = models.PositiveIntegerField(default=0, verbose_name="Dislikes Count")

    # Method tambahan
    def __str__(self):
        return f"Comment by {self.author} on {self.post.title}"

    def like(self):
        self.likes += 1
        self.save()

    def dislike(self):
        self.dislikes += 1
        self.save()

    def unlike(self):
        if self.likes > 0:
            self.likes -= 1
            self.save()

    def undislike(self):
        if self.dislikes > 0:
            self.dislikes -= 1
            self.save()
