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
from django.db.models import Q, Count, F
import json
from datetime import datetime, timedelta

# Import models dan forms yang sudah dibuat pada modul Post
from .models import ForumPost, Category, PostLike
from .forms import ForumPostForm

# ==================== POST CRUD VIEWS ====================

def forum_post_list(request):
    """
    Menampilkan semua post forum dengan filter, pencarian, dan pagination
    Mendukung AJAX untuk infinite scroll
    """
    # Base queryset - hanya post yang tidak dihapus
    posts = ForumPost.get_active_posts()
    
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
    
    # Filter post populer (minggu ini)
    popular_this_week = request.GET.get('popular', '')
    if popular_this_week:
        week_ago = datetime.now() - timedelta(days=7)
        posts = posts.filter(created_at__gte=week_ago).order_by('-views', '-created_at')
    
    # AJAX pagination request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        page = int(request.GET.get('page', 1))
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated_posts = posts[start:end]
        
        posts_data = []
        for post in paginated_posts:
            posts_data.append({
                'id': str(post.id),
                'title': post.title,
                'content': post.content[:200] + '...' if len(post.content) > 200 else post.content,
                'author': post.author.username,
                'author_id': post.author.id,
                'category': post.category.name if post.category else 'Uncategorized',
                'post_type': post.get_post_type_display(),
                'created_at': post.created_at.strftime('%d %b %Y, %H:%M'),
                'views': post.views,
                'like_count': post.like_count,
                'dislike_count': post.dislike_count,
                'comment_count': post.comment_count,
                'is_pinned': post.is_pinned,
                'image_url': post.image.url if post.image else None,
                'video_url': post.video_url,
                'detail_url': reverse('forum_post_detail', kwargs={'pk': post.id}),
            })
        
        return JsonResponse({
            'posts': posts_data,
            'has_next': len(paginated_posts) == per_page,
            'next_page': page + 1
        })
    
    # Statistik untuk template
    total_posts = posts.count()
    popular_posts = ForumPost.get_active_posts().order_by('-views')[:5]
    
    # Context untuk post 
    context = {
        'posts': posts[:20],  # Initial load 20 posts
        'post_types': ForumPost.POST_CATEGORY,
        'categories': Category.objects.all(),
        'selected_post_type': post_type_filter,
        'selected_category': category_filter,
        'search_query': search_query,
        'total_posts': total_posts,
        'popular_posts': popular_posts,
        'load_more_url': reverse('forum_post_list') + '?ajax=1&'
    }
    return render(request, 'forum/post_list.html', context)

def forum_post_detail(request, pk):
    """
    Menampilkan detail post dan increment views
    Mendukung AJAX untuk like/dislike dan komentar
    """
    try:
        # Untuk admin, tampilkan semua post termasuk yang dihapus
        if request.user.is_superuser:
            post = get_object_or_404(ForumPost, id=pk)
        else:
            post = get_object_or_404(ForumPost, id=pk, is_deleted=False)
    except:
        messages.error(request, 'Post tidak ditemukan atau telah dihapus.')
        return redirect('forum_post_list')
    
    # Increment views count (AJAX compatible)
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
    
    # AJAX request untuk data post saja
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id': str(post.id),
            'title': post.title,
            'content': post.content,
            'author': post.author.username,
            'author_id': post.author.id,
            'category': post.category.name if post.category else 'Uncategorized',
            'post_type': post.get_post_type_display(),
            'created_at': post.created_at.strftime('%d %b %Y, %H:%M'),
            'updated_at': post.updated_at.strftime('%d %b %Y, %H:%M') if post.is_edited else None,
            'views': post.views,
            'like_count': post.like_count,
            'dislike_count': post.dislike_count,
            'comment_count': post.comment_count,
            'is_pinned': post.is_pinned,
            'image_url': post.image.url if post.image else None,
            'video_url': post.video_url,
            'can_edit': post.can_edit(request.user) if request.user.is_authenticated else False,
            'can_delete': post.can_delete(request.user) if request.user.is_authenticated else False,
            'user_like': user_like.is_like if user_like else None,
        })
    
    context = {
        'post': post,
        'related_posts': related_posts,
        'user_like': user_like,
        'likes_count': post.like_count,
        'dislikes_count': post.dislike_count,
        'comment_count': post.comment_count,
    }
    return render(request, 'forum/post_detail.html', context)

@login_required
def create_forum_post(request):
    """
    Membuat post forum baru dengan support AJAX
    """
    if request.method == "POST":
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            
            # Update counters awal
            post.update_all_counts()
            
            post.save()
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Post berhasil dibuat!',
                    'post_id': str(post.id),
                    'redirect_url': reverse('forum_post_detail', kwargs={'pk': post.id})
                })
            
            messages.success(request, 'Post berhasil dibuat!')
            return redirect('forum_post_detail', pk=post.id)
        else:
            # AJAX response dengan error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Terjadi kesalahan. Silakan periksa form Anda.',
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
    else:
        form = ForumPostForm()
    
    # AJAX GET request - return form HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form_html = render(request, 'forum/partials/post_form.html', {'form': form}).content.decode('utf-8')
        return JsonResponse({'form_html': form_html})
    
    return render(request, 'forum/post_form.html', {
        'form': form,
        'title': 'Buat Post Baru'
    })

@login_required
def update_forum_post(request, pk):
    """
    Update post forum dengan support AJAX
    """
    try:
        post = get_object_or_404(ForumPost, id=pk)
        
        # Cek apakah user adalah author atau superuser
        if not post.can_edit(request.user):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Anda tidak memiliki izin untuk mengedit post ini.'
                }, status=403)
            messages.error(request, 'Anda tidak memiliki izin untuk mengedit post ini.')
            return redirect('forum_post_detail', pk=pk)
        
        if request.method == "POST":
            form = ForumPostForm(request.POST, request.FILES, instance=post)
            if form.is_valid():
                updated_post = form.save()
                
                # AJAX response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Post berhasil diupdate!',
                        'post_id': str(updated_post.id),
                        'redirect_url': reverse('forum_post_detail', kwargs={'pk': updated_post.id})
                    })
                
                messages.success(request, 'Post berhasil diupdate!')
                return redirect('forum_post_detail', pk=post.id)
            else:
                # AJAX response dengan error
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Terjadi kesalahan. Silakan periksa form Anda.',
                        'errors': form.errors
                    }, status=400)
                
                messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
        else:
            form = ForumPostForm(instance=post)
        
        # AJAX GET request - return form HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form_html = render(request, 'forum/partials/post_form.html', {
                'form': form, 
                'post': post
            }).content.decode('utf-8')
            return JsonResponse({'form_html': form_html})
        
        return render(request, 'forum/post_form.html', {
            'form': form,
            'title': 'Edit Post',
            'post': post
        })
    except ForumPost.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Post tidak ditemukan.'
            }, status=404)
        messages.error(request, 'Post tidak ditemukan.')
        return redirect('forum_post_list')

@login_required
def delete_forum_post(request, pk):
    """
    Hapus post forum (soft delete) dengan support AJAX
    """
    try:
        post = get_object_or_404(ForumPost, id=pk)
        
        # Cek apakah user adalah author atau superuser
        if not post.can_delete(request.user):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Anda tidak memiliki izin untuk menghapus post ini.'
                }, status=403)
            messages.error(request, 'Anda tidak memiliki izin untuk menghapus post ini.')
            return redirect('forum_post_detail', pk=pk)
        
        if request.method == "POST":
            post.soft_delete()
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Post berhasil dihapus!',
                    'redirect_url': reverse('forum_post_list')
                })
            
            messages.success(request, 'Post berhasil dihapus!')
            return redirect('forum_post_list')
        
        # AJAX GET request - return confirmation HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            confirm_html = render(request, 'forum/partials/post_confirm_delete.html', {'post': post}).content.decode('utf-8')
            return JsonResponse({'confirm_html': confirm_html})
        
        return render(request, 'forum/post_confirm_delete.html', {'post': post})
    except ForumPost.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Post tidak ditemukan.'
            }, status=404)
        messages.error(request, 'Post tidak ditemukan.')
        return redirect('forum_post_list')

# ==================== POST INTERACTION VIEWS (AJAX) ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def like_post(request, pk):
    """
    Like sebuah post menggunakan model PostLike - FULL AJAX
    """
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
                message = 'Like dihapus'
            else:
                # Jika sebelumnya dislike, ubah menjadi like
                post_like.is_like = True
                post_like.save()
                action = 'changed_to_like'
                message = 'Diubah menjadi like'
        except PostLike.DoesNotExist:
            # Jika belum, buat like baru
            PostLike.objects.create(post=post, user=user, is_like=True)
            action = 'like'
            message = 'Post dilike'
        
        # Get updated counts from model (already updated via signal)
        likes_count = post.like_count
        dislikes_count = post.dislike_count
        
        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
            'user_like_status': True if action in ['like', 'changed_to_like'] else None
        })
        
    except ForumPost.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': 'Post tidak ditemukan.'
        }, status=404)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def dislike_post(request, pk):
    """
    Dislike sebuah post menggunakan model PostLike - FULL AJAX
    """
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
                message = 'Dislike dihapus'
            else:
                # Jika sebelumnya like, ubah menjadi dislike
                post_like.is_like = False
                post_like.save()
                action = 'changed_to_dislike'
                message = 'Diubah menjadi dislike'
        except PostLike.DoesNotExist:
            # Jika belum, buat dislike baru
            PostLike.objects.create(post=post, user=user, is_like=False)
            action = 'dislike'
            message = 'Post didislike'
        
        # Get updated counts from model (already updated via signal)
        likes_count = post.like_count
        dislikes_count = post.dislike_count
        
        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
            'user_like_status': False if action in ['dislike', 'changed_to_dislike'] else None
        })
        
    except ForumPost.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': 'Post tidak ditemukan.'
        }, status=404)

@login_required
@require_http_methods(["POST"])
def pin_post(request, pk):
    """
    Pin post (hanya untuk superuser/staff) - AJAX compatible
    """
    if not request.user.is_superuser and not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Hanya admin yang bisa memin post!'
            }, status=403)
        messages.error(request, 'Hanya admin yang bisa memin post!')
        return redirect('forum_post_detail', pk=pk)
    
    try:
        post = get_object_or_404(ForumPost, id=pk)
        post.pin()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Post telah dipin!',
                'is_pinned': True
            })
        
        messages.success(request, 'Post telah dipin!')
    except ForumPost.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Post tidak ditemukan.'
            }, status=404)
        messages.error(request, 'Post tidak ditemukan.')
    
    return redirect('forum_post_detail', pk=pk)

@login_required
@require_http_methods(["POST"])
def unpin_post(request, pk):
    """
    Unpin post (hanya untuk superuser/staff) - AJAX compatible
    """
    if not request.user.is_superuser and not request.user.is_staff:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Hanya admin yang bisa unpin post!'
            }, status=403)
        messages.error(request, 'Hanya admin yang bisa unpin post!')
        return redirect('forum_post_detail', pk=pk)
    
    try:
        post = get_object_or_404(ForumPost, id=pk)
        post.unpin()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Post telah diunpin!',
                'is_pinned': False
            })
        
        messages.info(request, 'Post telah diunpin!')
    except ForumPost.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Post tidak ditemukan.'
            }, status=404)
        messages.error(request, 'Post tidak ditemukan.')
    
    return redirect('forum_post_detail', pk=pk)

# ==================== USER-SPECIFIC VIEWS ====================

@login_required
def my_posts(request):
    """
    Menampilkan post milik user yang login dengan AJAX support
    """
    posts = ForumPost.objects.filter(author=request.user, is_deleted=False).order_by('-created_at')
    
    # AJAX request untuk data post user
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        posts_data = []
        for post in posts:
            posts_data.append({
                'id': str(post.id),
                'title': post.title,
                'content': post.content[:150] + '...' if len(post.content) > 150 else post.content,
                'created_at': post.created_at.strftime('%d %b %Y'),
                'views': post.views,
                'like_count': post.like_count,
                'comment_count': post.comment_count,
                'is_pinned': post.is_pinned,
                'detail_url': reverse('forum_post_detail', kwargs={'pk': post.id}),
                'edit_url': reverse('update_forum_post', kwargs={'pk': post.id}),
            })
        
        return JsonResponse({'posts': posts_data})
    
    context = {
        'posts': posts,
        'title': 'Post Saya'
    }
    return render(request, 'forum/post_list.html', context)

@login_required
def my_pinned_posts(request):
    """
    Menampilkan post yang dipin (untuk admin) dengan AJAX support
    """
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa mengakses halaman ini!')
        return redirect('forum_post_list')
    
    posts = ForumPost.get_pinned_posts()
    
    context = {
        'posts': posts,
        'title': 'Post yang Dipin'
    }
    return render(request, 'forum/post_list.html', context)

# ==================== API VIEWS (JSON/XML) ====================

def show_forum_json(request):
    """Mengembalikan semua post forum dalam format JSON"""
    post_list = ForumPost.get_active_posts().order_by('-created_at')
    json_data = serializers.serialize("json", post_list)
    return HttpResponse(json_data, content_type="application/json")

def show_forum_xml(request):
    """Mengembalikan semua post forum dalam format XML"""
    post_list = ForumPost.get_active_posts().order_by('-created_at')
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

# ==================== STATISTICS VIEWS (Admin) ====================

def forum_statistics(request):
    """
    Menampilkan statistik forum dengan data real-time
    """
    total_posts = ForumPost.get_active_posts().count()
    total_views = ForumPost.get_active_posts().aggregate(total_views=Count('views'))['total_views'] or 0
    
    # Total likes dan dislikes dari model PostLike
    total_likes = PostLike.objects.filter(is_like=True).count()
    total_dislikes = PostLike.objects.filter(is_like=False).count()
    
    # Posts per category dengan annotation
    categories_data = Category.objects.annotate(
        post_count=Count('forumpost', filter=Q(forumpost__is_deleted=False))
    ).values('name', 'id', 'post_count')
    
    # Posts per post type
    post_types_data = []
    for post_type_code, post_type_name in ForumPost.POST_CATEGORY:
        count = ForumPost.objects.filter(post_type=post_type_code, is_deleted=False).count()
        post_types_data.append({
            'name': post_type_name,
            'code': post_type_code,
            'count': count
        })
    
    # Most popular posts (berdasarkan views)
    popular_posts = ForumPost.get_active_posts().order_by('-views')[:10]
    
    # Most liked posts (berdasarkan like_count yang sudah di-denormalize)
    most_liked_posts = ForumPost.get_active_posts().order_by('-like_count')[:10]
    
    # Most active authors
    active_authors = ForumPost.get_active_posts().values(
        'author__username', 'author_id'
    ).annotate(
        post_count=Count('id'),
        total_views=Count('views'),
        total_likes=Count('likes', filter=Q(likes__is_like=True))
    ).order_by('-post_count')[:10]
    
    # AJAX request untuk chart data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'categories_data': list(categories_data),
            'post_types_data': post_types_data,
            'total_stats': {
                'posts': total_posts,
                'views': total_views,
                'likes': total_likes,
                'dislikes': total_dislikes,
            }
        })
    
    context = {
        'total_posts': total_posts,
        'total_views': total_views,
        'total_likes': total_likes,
        'total_dislikes': total_dislikes,
        'categories_data': categories_data,
        'post_types_data': post_types_data,
        'popular_posts': popular_posts,
        'most_liked_posts': most_liked_posts,
        'active_authors': active_authors,
    }
    return render(request, 'forum/statistics.html', context)