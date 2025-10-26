from django.contrib import admin
from .models import Post, PostInteraction

# Register your models here.


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at", "is_deleted")
    list_filter = ("is_deleted", "created_at")
    search_fields = ("title", "content", "user__username")


@admin.register(PostInteraction)
class PostInteractionAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "interaction_type", "created_at")
    list_filter = ("interaction_type", "created_at")
    search_fields = ("user__username", "post__title")
