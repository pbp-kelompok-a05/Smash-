# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from post.models import Post


def home(request):
    """
    Homepage view yang menampilkan daftar post
    Accessible to all users (authenticated and anonymous)
    """
    # Tambahkan context jika perlu
    posts = Post.objects.all().order_by("-created_at")
    return render(request, "main.html", {"posts": posts})
