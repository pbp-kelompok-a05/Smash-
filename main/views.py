# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from post.models import Post

@login_required
def home(request):
    """
    Homepage view yang menampilkan daftar post
    Hanya bisa diakses oleh user yang sudah login
    """
    # Tambahkan context jika perlu
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'main.html', {'posts': posts})