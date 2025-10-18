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
        ('discussion', 'Discussion'),
        ('question', 'Question'),
        ('review', 'Review'),
        ('nostalgia', 'Nostalgia')
    ]

    # Define attribute yang dibutuhkan 
    # Judul post
    title = models.CharField(max_length=255, verbose_name="Post Title")
    # Content post -> Isi dari Post
    content = models.TextField(verbose_name="content")
    # Author atau penulis Post
    author = models.CharField(max_length=100, choices=post_kategory, default="category", verbose_name="Post Category")
    # Timestamp untuk pembuatan dan update post
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    update_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    # Addition -> Pin Post
    is_pinned = models.BooleanField(default=False, verbose_name="Pinned 📌")
    
    # Method tambahan 
    # Return Post title
    def __str__(self):
        return self.title
