import uuid
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core import serializers
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
import json

from .models import ForumPost, Category
from .forms import ForumPostForm

# ==================== AUTHENTICATION VIEWS ====================

# ==================== POST CRUD VIEWS ====================

def forum_post_list(request):
    """Menampilkan semua post forum dengan filter dan pencarian"""
    posts = ForumPost.objects.all().order_by('-is_pinned', '-created_at')
    
    # Filter berdasarkan kategori
    category_filter = request.GET.get('category', '')
    if category_filter:
        posts = posts.filter(category=category_filter)
    
    # Pencarian berdasarkan judul atau konten
    search_query = request.GET.get('search', '')
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query)
        )
    
    # Statistik untuk template
    total_posts = posts.count()
    popular_posts = ForumPost.objects.all().order_by('-views')[:5]
    
    context = {
        'posts': posts,
        'categories': ForumPost.post_kategory,
        'selected_category': category_filter,
        'search_query': search_query,
        'total_posts': total_posts,
        'popular_posts': popular_posts,
    }
    return render(request, 'forum/post_list.html', context)

def forum_post_detail(request, post_id):
    """Menampilkan detail post dan increment views"""
    post = get_object_or_404(ForumPost, id=post_id)
    
    # Increment views count
    post.increment_views()
    
    # Get related posts (same category)
    related_posts = ForumPost.objects.filter(
        category=post.category
    ).exclude(id=post_id).order_by('-created_at')[:3]
    
    context = {
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'forum/post_detail.html', context)

@login_required
def create_forum_post(request):
    """Membuat post forum baru"""
    if request.method == "POST":
        form = ForumPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post berhasil dibuat!')
            return redirect('forum_post_detail', post_id=post.id)
    else:
        form = ForumPostForm()
    
    return render(request, 'forum/post_form.html', {
        'form': form,
        'title': 'Buat Post Baru'
    })

@login_required
def update_forum_post(request, post_id):
    """Update post forum"""
    post = get_object_or_404(ForumPost, id=post_id)
    
    # Cek apakah user adalah author atau superuser
    if post.author != request.user and not request.user.is_superuser:
        messages.error(request, 'Anda tidak memiliki izin untuk mengedit post ini.')
        return redirect('forum_post_detail', post_id=post_id)
    
    if request.method == "POST":
        form = ForumPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post berhasil diupdate!')
            return redirect('forum_post_detail', post_id=post.id)
    else:
        form = ForumPostForm(instance=post)
    
    return render(request, 'forum/post_form.html', {
        'form': form,
        'title': 'Edit Post',
        'post': post
    })

@login_required
def delete_forum_post(request, post_id):
    """Hapus post forum"""
    post = get_object_or_404(ForumPost, id=post_id)
    
    # Cek apakah user adalah author atau superuser
    if post.author != request.user and not request.user.is_superuser:
        messages.error(request, 'Anda tidak memiliki izin untuk menghapus post ini.')
        return redirect('forum_post_detail', post_id=post_id)
    
    if request.method == "POST":
        post.delete()
        messages.success(request, 'Post berhasil dihapus!')
        return redirect('forum_post_list')
    
    return render(request, 'forum/post_confirm_delete.html', {'post': post})

# ==================== POST INTERACTION VIEWS ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def like_post(request, post_id):
    """Like sebuah post"""
    post = get_object_or_404(ForumPost, id=post_id)
    
    # Untuk sederhana, kita asumsikan user bisa like multiple times
    # Dalam implementasi real, Anda mungkin perlu model Like terpisah
    post.like()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'likes': post.likes,
            'dislikes': post.dislikes
        })
    
    messages.success(request, 'Post telah dilike!')
    return redirect('forum_post_detail', post_id=post_id)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def dislike_post(request, post_id):
    """Dislike sebuah post"""
    post = get_object_or_404(ForumPost, id=post_id)
    post.dislike()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'likes': post.likes,
            'dislikes': post.dislikes
        })
    
    messages.info(request, 'Post telah didislike!')
    return redirect('forum_post_detail', post_id=post_id)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def unlike_post(request, post_id):
    """Unlike sebuah post"""
    post = get_object_or_404(ForumPost, id=post_id)
    post.unlike()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'likes': post.likes,
            'dislikes': post.dislikes
        })
    
    messages.info(request, 'Like telah dihapus!')
    return redirect('forum_post_detail', post_id=post_id)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def undislike_post(request, post_id):
    """Hapus dislike dari post"""
    post = get_object_or_404(ForumPost, id=post_id)
    post.undislike()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'likes': post.likes,
            'dislikes': post.dislikes
        })
    
    messages.info(request, 'Dislike telah dihapus!')
    return redirect('forum_post_detail', post_id=post_id)

@login_required
@require_http_methods(["POST"])
def pin_post(request, post_id):
    """Pin post (hanya untuk superuser/staff)"""
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa memin post!')
        return redirect('forum_post_detail', post_id=post_id)
    
    post = get_object_or_404(ForumPost, id=post_id)
    post.pin()
    
    messages.success(request, 'Post telah dipin!')
    return redirect('forum_post_detail', post_id=post_id)

@login_required
@require_http_methods(["POST"])
def unpin_post(request, post_id):
    """Unpin post (hanya untuk superuser/staff)"""
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa unpin post!')
        return redirect('forum_post_detail', post_id=post_id)
    
    post = get_object_or_404(ForumPost, id=post_id)
    post.unpin()
    
    messages.info(request, 'Post telah diunpin!')
    return redirect('forum_post_detail', post_id=post_id)

# ==================== USER-SPECIFIC VIEWS ====================

@login_required
def my_posts(request):
    """Menampilkan post milik user yang login"""
    posts = ForumPost.objects.filter(author=request.user).order_by('-created_at')
    
    context = {
        'posts': posts,
        'title': 'Post Saya'
    }
    return render(request, 'forum/post_list.html', context)

@login_required
def my_pinned_posts(request):
    """Menampilkan post yang dipin (untuk admin)"""
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa mengakses halaman ini!')
        return redirect('forum_post_list')
    
    posts = ForumPost.objects.filter(is_pinned=True).order_by('-created_at')
    
    context = {
        'posts': posts,
        'title': 'Post yang Dipin'
    }
    return render(request, 'forum/post_list.html', context)

# ==================== API VIEWS (JSON/XML) ====================

def show_forum_json(request):
    """Mengembalikan semua post forum dalam format JSON"""
    post_list = ForumPost.objects.all().order_by('-created_at')
    json_data = serializers.serialize("json", post_list)
    return HttpResponse(json_data, content_type="application/json")

def show_forum_xml(request):
    """Mengembalikan semua post forum dalam format XML"""
    post_list = ForumPost.objects.all().order_by('-created_at')
    xml_data = serializers.serialize("xml", post_list)
    return HttpResponse(xml_data, content_type="application/xml")

def show_forum_json_by_id(request, post_id):
    """Mengembalikan post forum tertentu dalam format JSON"""
    try:
        post = ForumPost.objects.get(id=post_id)
        json_data = serializers.serialize("json", [post])
        return HttpResponse(json_data, content_type="application/json")
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Post tidak ditemukan'}, status=404)

def show_forum_xml_by_id(request, post_id):
    """Mengembalikan post forum tertentu dalam format XML"""
    try:
        post = ForumPost.objects.get(id=post_id)
        xml_data = serializers.serialize("xml", [post])
        return HttpResponse(xml_data, content_type="application/xml")
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Post tidak ditemukan'}, status=404)

def show_forum_json_by_category(request, category):
    """Mengembalikan post forum berdasarkan kategori dalam format JSON"""
    post_list = ForumPost.objects.filter(category=category).order_by('-created_at')
    json_data = serializers.serialize("json", post_list)
    return HttpResponse(json_data, content_type="application/json")

# ==================== STATISTICS VIEWS ====================

def forum_statistics(request):
    """Menampilkan statistik forum"""
    total_posts = ForumPost.objects.count()
    total_views = ForumPost.objects.aggregate(total_views=Count('views'))['total_views']
    total_likes = ForumPost.objects.aggregate(total_likes=Count('likes'))['total_likes']
    
    # Posts per category
    categories_data = []
    for category_code, category_name in ForumPost.post_kategory:
        count = ForumPost.objects.filter(category=category_code).count()
        categories_data.append({
            'name': category_name,
            'code': category_code,
            'count': count
        })
    
    # Most popular posts
    popular_posts = ForumPost.objects.all().order_by('-views')[:10]
    most_liked_posts = ForumPost.objects.all().order_by('-likes')[:10]
    
    context = {
        'total_posts': total_posts,
        'total_views': total_views,
        'total_likes': total_likes,
        'categories_data': categories_data,
        'popular_posts': popular_posts,
        'most_liked_posts': most_liked_posts,
    }
    return render(request, 'forum/statistics.html', context)
