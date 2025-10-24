from django.contrib import admin
from .models import Comment, CommentInteraction

# Register your models here.


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "post",
        "content",
        "likes_count",
        "dislikes_count",
        "created_at",
    ]
    list_filter = ["created_at", "is_deleted"]
    search_fields = ["content", "user__username"]


@admin.register(CommentInteraction)
class CommentInteractionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "comment", "interaction_type", "created_at"]
    list_filter = ["interaction_type", "created_at"]
    search_fields = ["user__username", "comment__content"]
