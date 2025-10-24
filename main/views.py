# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from post.models import Post

@login_required
def home(request):
    """
    Homepage view yang menampilkan daftar post
    """
    posts = Post.objects.filter(is_deleted=False).order_by('-created_at')
    
    # Annotate each post with like and comment counts
    for post in posts:
        post.like_count = post.likes.count()
        post.comment_count = post.comments.filter(is_deleted=False).count()
    
    context = {
        'posts': posts,
        'user': request.user
    }
    return render(request, 'main/main.html', context)

@login_required
def profile(request):
    """
    Profile view
    """
    context = {
        'user': request.user
    }
    return render(request, 'main/profile.html', context)