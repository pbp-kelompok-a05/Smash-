# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from post.models import Post
from ads.models import Advertisement


def home(request):
    """
    Homepage view yang menampilkan daftar post
    Accessible to all users (authenticated and anonymous)
    """
    # Tambahkan context jika perlu
    posts = Post.objects.all().order_by("-created_at")
    popup_ad = (
        Advertisement.objects.filter(
            ad_type="popup", is_active=True, image__isnull=False
        ).order_by("-created_at").first()
    )
    return render(request, "main.html", {"posts": posts, "popup_ad": popup_ad})
