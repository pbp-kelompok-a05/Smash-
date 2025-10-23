# Import library yang dibutuhkan 
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

from .models import ForumPost, Category, PostLike
from .forms import ForumPostForm

# ==================== AUTHENTICATION VIEWS ====================

# ==================== POST CRUD VIEWS ====================

def forum_post_list(request):
    """Menampilkan semua post forum dengan filter dan pencarian"""
    posts = ForumPost.objects.filter(is_deleted=False).order_by('-is_pinned', '-created_at')
    
    # Filter berdasarkan tipe post
    post_type_filter = request.GET.get('post_type', '')
    if post_type_filter:
        posts = posts.filter(post_type=post_type_filter)
    
    # Filter berdasarkan kategori
    category_filter = request.GET.get('category', '')
    if category_filter:
        posts = posts.filter(category_id=category_filter)
    
    # Pencarian berdasarkan judul atau konten
    search_query = request.GET.get('search', '')
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query)
        )
    
    # Statistik untuk template
    total_posts = posts.count()
    popular_posts = ForumPost.objects.filter(is_deleted=False).order_by('-views')[:5]
    
    # Context untuk post 
    context = {
        'posts': posts,
        'post_types': ForumPost.POST_CATEGORY,
        'categories': Category.objects.all(),
        'selected_post_type': post_type_filter,
        'selected_category': category_filter,
        'search_query': search_query,
        'total_posts': total_posts,
        'popular_posts': popular_posts,
    }
    return render(request, 'forum/post_list.html', context)

def forum_post_detail(request, pk):
    """Menampilkan detail post dan increment views"""
    try:
        # Untuk admin, tampilkan semua post termasuk yang dihapus
        if request.user.is_superuser:
            post = get_object_or_404(ForumPost, id=pk)
        else:
            post = get_object_or_404(ForumPost, id=pk, is_deleted=False)
    except:
        messages.error(request, 'Post tidak ditemukan atau telah dihapus.')
        return redirect('forum_post_list')
    
    # Increment views count
    post.increment_views()
    
    # Get related posts (same category)
    related_posts = ForumPost.objects.filter(
        category=post.category,
        is_deleted=False
    ).exclude(id=pk).order_by('-created_at')[:3]
    
    # Check if user has liked/disliked this post
    user_like = None
    if request.user.is_authenticated:
        try:
            user_like = PostLike.objects.get(post=post, user=request.user)
        except PostLike.DoesNotExist:
            pass
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'user_like': user_like,
        'likes_count': post.get_likes_count(),
        'dislikes_count': post.get_dislikes_count(),
        'comment_count': post.get_comment_count(),
    }
    return render(request, 'forum/post_detail.html', context)

@login_required
def create_forum_post(request):
    """Membuat post forum baru"""
    if request.method == "POST":
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post berhasil dibuat!')
            return redirect('forum_post_detail', pk=post.id)
        else:
            messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
    else:
        form = ForumPostForm()
    
    return render(request, 'forum/post_form.html', {
        'form': form,
        'title': 'Buat Post Baru'
    })

@login_required
def update_forum_post(request, pk):
    """Update post forum"""
    try:
        post = get_object_or_404(ForumPost, id=pk)
        
        # Cek apakah user adalah author atau superuser
        if post.author != request.user and not request.user.is_superuser:
            messages.error(request, 'Anda tidak memiliki izin untuk mengedit post ini.')
            return redirect('forum_post_detail', pk=pk)
        
        if request.method == "POST":
            form = ForumPostForm(request.POST, request.FILES, instance=post)
            if form.is_valid():
                form.save()
                messages.success(request, 'Post berhasil diupdate!')
                return redirect('forum_post_detail', pk=post.id)
            else:
                messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
        else:
            form = ForumPostForm(instance=post)
        
        return render(request, 'forum/post_form.html', {
            'form': form,
            'title': 'Edit Post',
            'post': post
        })
    except:
        messages.error(request, 'Post tidak ditemukan.')
        return redirect('forum_post_list')

@login_required
def delete_forum_post(request, pk):
    """Hapus post forum (soft delete)"""
    try:
        post = get_object_or_404(ForumPost, id=pk)
        
        # Cek apakah user adalah author atau superuser
        if post.author != request.user and not request.user.is_superuser:
            messages.error(request, 'Anda tidak memiliki izin untuk menghapus post ini.')
            return redirect('forum_post_detail', pk=pk)
        
        if request.method == "POST":
            post.soft_delete()
            messages.success(request, 'Post berhasil dihapus!')
            return redirect('forum_post_list')
        
        return render(request, 'forum/post_confirm_delete.html', {'post': post})
    except:
        messages.error(request, 'Post tidak ditemukan.')
        return redirect('forum_post_list')

# ==================== POST INTERACTION VIEWS ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def like_post(request, pk):
    """Like sebuah post menggunakan model PostLike"""
    try:
        post = get_object_or_404(ForumPost, id=pk, is_deleted=False)
        user = request.user
        
        # Cek apakah user sudah memberikan like/dislike sebelumnya
        try:
            post_like = PostLike.objects.get(post=post, user=user)
            if post_like.is_like:
                # Jika sudah like, hapus like (unlike)
                post_like.delete()
                action = 'unlike'
            else:
                # Jika sebelumnya dislike, ubah menjadi like
                post_like.is_like = True
                post_like.save()
                action = 'changed_to_like'
        except PostLike.DoesNotExist:
            # Jika belum, buat like baru
            PostLike.objects.create(post=post, user=user, is_like=True)
            action = 'like'
        
        likes_count = post.get_likes_count()
        dislikes_count = post.get_dislikes_count()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'action': action,
                'likes_count': likes_count,
                'dislikes_count': dislikes_count
            })
        
        messages.success(request, 'Post telah dilike!')
        return redirect('forum_post_detail', pk=pk)
        
    except ForumPost.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Post tidak ditemukan'}, status=404)
        messages.error(request, 'Post tidak ditemukan.')
        return redirect('forum_post_list')

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def dislike_post(request, pk):
    """Dislike sebuah post menggunakan model PostLike"""
    try:
        post = get_object_or_404(ForumPost, id=pk, is_deleted=False)
        user = request.user
        
        # Cek apakah user sudah memberikan like/dislike sebelumnya
        try:
            post_like = PostLike.objects.get(post=post, user=user)
            if not post_like.is_like:
                # Jika sudah dislike, hapus dislike (undislike)
                post_like.delete()
                action = 'undislike'
            else:
                # Jika sebelumnya like, ubah menjadi dislike
                post_like.is_like = False
                post_like.save()
                action = 'changed_to_dislike'
        except PostLike.DoesNotExist:
            # Jika belum, buat dislike baru
            PostLike.objects.create(post=post, user=user, is_like=False)
            action = 'dislike'
        
        likes_count = post.get_likes_count()
        dislikes_count = post.get_dislikes_count()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'action': action,
                'likes_count': likes_count,
                'dislikes_count': dislikes_count
            })
        
        messages.info(request, 'Post telah didislike!')
        return redirect('forum_post_detail', pk=pk)
        
    except ForumPost.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Post tidak ditemukan'}, status=404)
        messages.error(request, 'Post tidak ditemukan.')
        return redirect('forum_post_list')

@login_required
@require_http_methods(["POST"])
def pin_post(request, pk):
    """Pin post (hanya untuk superuser/staff)"""
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa memin post!')
        return redirect('forum_post_detail', pk=pk)
    
    try:
        post = get_object_or_404(ForumPost, id=pk)
        post.pin()
        messages.success(request, 'Post telah dipin!')
    except:
        messages.error(request, 'Post tidak ditemukan.')
    
    return redirect('forum_post_detail', pk=pk)

@login_required
@require_http_methods(["POST"])
def unpin_post(request, pk):
    """Unpin post (hanya untuk superuser/staff)"""
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa unpin post!')
        return redirect('forum_post_detail', pk=pk)
    
    try:
        post = get_object_or_404(ForumPost, id=pk)
        post.unpin()
        messages.info(request, 'Post telah diunpin!')
    except:
        messages.error(request, 'Post tidak ditemukan.')
    
    return redirect('forum_post_detail', pk=pk)

# ==================== USER-SPECIFIC VIEWS ====================

@login_required
def my_posts(request):
    """Menampilkan post milik user yang login"""
    posts = ForumPost.objects.filter(author=request.user, is_deleted=False).order_by('-created_at')
    
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
    
    posts = ForumPost.objects.filter(is_pinned=True, is_deleted=False).order_by('-created_at')
    
    context = {
        'posts': posts,
        'title': 'Post yang Dipin'
    }
    return render(request, 'forum/post_list.html', context)

# ==================== API VIEWS (JSON/XML) ====================

def show_forum_json(request):
    """Mengembalikan semua post forum dalam format JSON"""
    post_list = ForumPost.objects.filter(is_deleted=False).order_by('-created_at')
    json_data = serializers.serialize("json", post_list)
    return HttpResponse(json_data, content_type="application/json")

def show_forum_xml(request):
    """Mengembalikan semua post forum dalam format XML"""
    post_list = ForumPost.objects.filter(is_deleted=False).order_by('-created_at')
    xml_data = serializers.serialize("xml", post_list)
    return HttpResponse(xml_data, content_type="application/xml")

def show_forum_json_by_id(request, pk):
    """Mengembalikan post forum tertentu dalam format JSON"""
    try:
        post = ForumPost.objects.get(id=pk, is_deleted=False)
        json_data = serializers.serialize("json", [post])
        return HttpResponse(json_data, content_type="application/json")
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Post tidak ditemukan'}, status=404)

def show_forum_xml_by_id(request, pk):
    """Mengembalikan post forum tertentu dalam format XML"""
    try:
        post = ForumPost.objects.get(id=pk, is_deleted=False)
        xml_data = serializers.serialize("xml", [post])
        return HttpResponse(xml_data, content_type="application/xml")
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Post tidak ditemukan'}, status=404)

def show_forum_json_by_category(request, category_id):
    """Mengembalikan post forum berdasarkan kategori dalam format JSON"""
    post_list = ForumPost.objects.filter(category_id=category_id, is_deleted=False).order_by('-created_at')
    json_data = serializers.serialize("json", post_list)
    return HttpResponse(json_data, content_type="application/json")

# ==================== STATISTICS VIEWS ====================

def forum_statistics(request):
    """Menampilkan statistik forum"""
    total_posts = ForumPost.objects.filter(is_deleted=False).count()
    total_views = ForumPost.objects.filter(is_deleted=False).aggregate(total_views=Count('views'))['total_views'] or 0
    
    # Total likes dan dislikes dari model PostLike
    total_likes = PostLike.objects.filter(is_like=True).count()
    total_dislikes = PostLike.objects.filter(is_like=False).count()
    
    # Posts per category
    categories_data = []
    for category in Category.objects.all():
        count = ForumPost.objects.filter(category=category, is_deleted=False).count()
        categories_data.append({
            'name': category.name,
            'id': category.id,
            'count': count
        })
    
    # Posts per post type
    post_types_data = []
    for post_type_code, post_type_name in ForumPost.POST_CATEGORY:
        count = ForumPost.objects.filter(post_type=post_type_code, is_deleted=False).count()
        post_types_data.append({
            'name': post_type_name,
            'code': post_type_code,
            'count': count
        })
    
    # Most popular posts
    popular_posts = ForumPost.objects.filter(is_deleted=False).order_by('-views')[:10]
    
    # Most liked posts (berdasarkan PostLike)
    most_liked_posts = ForumPost.objects.filter(is_deleted=False).annotate(
        like_count=Count('likes', filter=Q(likes__is_like=True))
    ).order_by('-like_count')[:10]
    
    context = {
        'total_posts': total_posts,
        'total_views': total_views,
        'total_likes': total_likes,
        'total_dislikes': total_dislikes,
        'categories_data': categories_data,
        'post_types_data': post_types_data,
        'popular_posts': popular_posts,
        'most_liked_posts': most_liked_posts,
    }
    return render(request, 'forum/statistics.html', context)