import uuid
import json
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core import serializers
from django.contrib import messages
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from datetime import datetime, timedelta

# Import models dan forms
from .models import ForumPost, Category, PostLike
from .forms import ForumPostForm


# ==================== UTILITY FUNCTIONS ====================

def _get_ajax_response(request, template_name, context=None):
    """
    Utility function untuk render AJAX response sebagai modal
    """
    if context is None:
        context = {}
    
    rendered_html = render(request, template_name, context).content.decode('utf-8')
    return JsonResponse({'modal_html': rendered_html})


def _get_post_data(post):
    """
    Utility function untuk serialize post data
    """
    return {
        'id': str(post.id),
        'title': post.title,
        'content': post.content,
        'excerpt': post.content[:200] + '...' if len(post.content) > 200 else post.content,
        'author': post.author.username if post.author else 'Unknown',
        'author_id': post.author.id if post.author else None,
        'category': post.category.name if post.category else 'Uncategorized',
        'category_id': post.category.id if post.category else None,
        'post_type': post.get_post_type_display(),
        'post_type_value': post.post_type,
        'created_at': post.created_at.strftime('%d %b %Y, %H:%M'),
        'updated_at': post.updated_at.strftime('%d %b %Y, %H:%M') if post.is_edited else None,
        'views': post.views,
        'like_count': post.like_count,
        'dislike_count': post.dislike_count,
        'comment_count': post.comment_count,
        'is_pinned': post.is_pinned,
        'is_edited': post.is_edited,
        'image_url': post.image.url if post.image else None,
        'video_url': post.video_url,
        'detail_url': reverse('forum_post_detail', kwargs={'pk': post.id}),
        'edit_url': reverse('update_forum_post', kwargs={'pk': post.id}) if post.author else None,
        'delete_url': reverse('delete_forum_post', kwargs={'pk': post.id}) if post.author else None,
    }


# ==================== POST CRUD VIEWS ====================

def forum_post_list(request):
    """
    Menampilkan semua post forum dengan filter, pencarian, dan pagination
    Mendukung AJAX untuk infinite scroll dan modal display
    
    Features:
    - Filter by post type dan category
    - Search functionality
    - Popular posts filter
    - AJAX pagination
    - Modal support untuk actions
    """
    try:
        # Base queryset - hanya post yang tidak dihapus
        posts = ForumPost.get_active_posts().select_related('author', 'category')
        
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
        
        # Ordering default
        posts = posts.order_by('-is_pinned', '-created_at')
        
        # AJAX pagination request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            page = int(request.GET.get('page', 1))
            per_page = 10
            start = (page - 1) * per_page
            end = start + per_page
            
            paginated_posts = posts[start:end]
            
            posts_data = [_get_post_data(post) for post in paginated_posts]
            
            return JsonResponse({
                'status': 'success',
                'posts': posts_data,
                'has_next': len(paginated_posts) == per_page,
                'next_page': page + 1
            })
        
        # Statistik untuk template
        total_posts = posts.count()
        popular_posts = ForumPost.get_active_posts().order_by('-views')[:5]
        pinned_posts = ForumPost.get_pinned_posts()
        
        context = {
            'posts': posts[:20],  # Initial load 20 posts
            'pinned_posts': pinned_posts,
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
    
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return render(request, 'forum/post_list.html', {
            'posts': ForumPost.get_active_posts()[:20],
            'categories': Category.objects.all()
        })


def forum_post_detail(request, pk):
    """
    Menampilkan detail post dan increment views
    Mendukung AJAX untuk data retrieval dan modal interactions
    
    Args:
        pk: UUID dari post yang akan ditampilkan
    """
    try:
        # Untuk admin, tampilkan semua post termasuk yang dihapus
        if request.user.is_superuser:
            post = get_object_or_404(ForumPost.objects.select_related('author', 'category'), id=pk)
        else:
            post = get_object_or_404(
                ForumPost.objects.select_related('author', 'category'), 
                id=pk, 
                is_deleted=False
            )
        
        # Increment views count
        post.increment_views()
        
        # Get related posts (same category)
        related_posts = ForumPost.objects.filter(
            category=post.category,
            is_deleted=False
        ).exclude(id=pk).select_related('author', 'category').order_by('-created_at')[:3]
        
        # Check if user has liked/disliked this post
        user_like = None
        if request.user.is_authenticated:
            try:
                user_like = PostLike.objects.get(post=post, user=request.user)
            except PostLike.DoesNotExist:
                pass
        
        # AJAX request untuk data post saja
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            post_data = _get_post_data(post)
            post_data.update({
                'can_edit': post.can_edit(request.user) if request.user.is_authenticated else False,
                'can_delete': post.can_delete(request.user) if request.user.is_authenticated else False,
                'user_like_status': user_like.is_like if user_like else None,
            })
            
            return JsonResponse({
                'status': 'success',
                'post': post_data
            })
        
        context = {
            'post': post,
            'related_posts': related_posts,
            'user_like': user_like,
        }
        return render(request, 'forum/post_detail.html', context)
        
    except ForumPost.DoesNotExist:
        messages.error(request, 'Post tidak ditemukan atau telah dihapus.')
        return redirect('forum_post_list')
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return redirect('forum_post_list')


@login_required
def create_forum_post(request):
    """
    Membuat post forum baru dengan support AJAX modal
    
    Features:
    - AJAX modal form display
    - Form validation dengan feedback
    - Automatic author assignment
    - Media upload handling
    """
    if request.method == "POST":
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                post = form.save(commit=False)
                post.author = request.user
                post.save()
                
                # AJAX response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Post berhasil dibuat!',
                        'post': _get_post_data(post),
                        'redirect_url': reverse('forum_post_detail', kwargs={'pk': post.id})
                    })
                
                messages.success(request, 'Post berhasil dibuat!')
                return redirect('forum_post_detail', pk=post.id)
                
            except Exception as e:
                error_msg = f'Terjadi kesalahan saat menyimpan post: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=500)
                messages.error(request, error_msg)
        else:
            # AJAX response dengan error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Terjadi kesalahan validasi.',
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
    else:
        form = ForumPostForm()
    
    # AJAX GET request - return modal HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return _get_ajax_response(
            request, 
            'forum/modals/post_form_modal.html', 
            {'form': form, 'title': 'Buat Post Baru', 'action_url': reverse('create_forum_post')}
        )
    
    return render(request, 'forum/post_form.html', {
        'form': form,
        'title': 'Buat Post Baru'
    })


@login_required
def update_forum_post(request, pk):
    """
    Update post forum dengan support AJAX modal
    
    Features:
    - Permission checking (author atau staff only)
    - AJAX modal form display
    - Pre-filled form data
    - Success/error feedback
    """
    try:
        post = get_object_or_404(ForumPost.objects.select_related('author'), id=pk)
        
        # Permission check
        if not post.can_edit(request.user):
            error_msg = 'Anda tidak memiliki izin untuk mengedit post ini.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                }, status=403)
            messages.error(request, error_msg)
            return redirect('forum_post_detail', pk=pk)
        
        if request.method == "POST":
            form = ForumPostForm(request.POST, request.FILES, instance=post)
            if form.is_valid():
                try:
                    updated_post = form.save()
                    
                    # AJAX response
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Post berhasil diupdate!',
                            'post': _get_post_data(updated_post),
                            'redirect_url': reverse('forum_post_detail', kwargs={'pk': updated_post.id})
                        })
                    
                    messages.success(request, 'Post berhasil diupdate!')
                    return redirect('forum_post_detail', pk=post.id)
                    
                except Exception as e:
                    error_msg = f'Terjadi kesalahan saat mengupdate post: {str(e)}'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'error',
                            'message': error_msg
                        }, status=500)
                    messages.error(request, error_msg)
            else:
                # AJAX response dengan error
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Terjadi kesalahan validasi.',
                        'errors': form.errors
                    }, status=400)
                
                messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
        else:
            form = ForumPostForm(instance=post)
        
        # AJAX GET request - return modal HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return _get_ajax_response(
                request,
                'forum/modals/post_form_modal.html',
                {
                    'form': form, 
                    'title': 'Edit Post', 
                    'post': post,
                    'action_url': reverse('update_forum_post', kwargs={'pk': pk})
                }
            )
        
        return render(request, 'forum/post_form.html', {
            'form': form,
            'title': 'Edit Post',
            'post': post
        })
        
    except ForumPost.DoesNotExist:
        error_msg = 'Post tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('forum_post_list')


@login_required
def delete_forum_post(request, pk):
    """
    Hapus post forum (soft delete) dengan support AJAX modal
    
    Features:
    - Permission checking (author atau staff only)
    - AJAX modal confirmation
    - Soft delete functionality
    - Success feedback
    """
    try:
        post = get_object_or_404(ForumPost.objects.select_related('author'), id=pk)
        
        # Permission check
        if not post.can_delete(request.user):
            error_msg = 'Anda tidak memiliki izin untuk menghapus post ini.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                }, status=403)
            messages.error(request, error_msg)
            return redirect('forum_post_detail', pk=pk)
        
        if request.method == "POST":
            try:
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
                
            except Exception as e:
                error_msg = f'Terjadi kesalahan saat menghapus post: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=500)
                messages.error(request, error_msg)
        
        # AJAX GET request - return confirmation modal HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return _get_ajax_response(
                request,
                'forum/modals/post_confirm_delete_modal.html',
                {'post': post}
            )
        
        return render(request, 'forum/post_confirm_delete.html', {'post': post})
        
    except ForumPost.DoesNotExist:
        error_msg = 'Post tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('forum_post_list')


# ==================== POST INTERACTION VIEWS (AJAX) ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def like_post(request, pk):
    """
    Like sebuah post - FULL AJAX
    
    Features:
    - Toggle like functionality
    - Auto-update counters
    - JSON response dengan status terbaru
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
        
        # Refresh post data dari database
        post.refresh_from_db()
        
        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'likes_count': post.like_count,
            'dislikes_count': post.dislike_count,
            'user_like_status': True if action in ['like', 'changed_to_like'] else None
        })
        
    except ForumPost.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': 'Post tidak ditemukan.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def dislike_post(request, pk):
    """
    Dislike sebuah post - FULL AJAX
    
    Features:
    - Toggle dislike functionality  
    - Auto-update counters
    - JSON response dengan status terbaru
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
        
        # Refresh post data dari database
        post.refresh_from_db()
        
        return JsonResponse({
            'status': 'success',
            'action': action,
            'message': message,
            'likes_count': post.like_count,
            'dislikes_count': post.dislike_count,
            'user_like_status': False if action in ['dislike', 'changed_to_dislike'] else None
        })
        
    except ForumPost.DoesNotExist:
        return JsonResponse({
            'status': 'error', 
            'message': 'Post tidak ditemukan.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


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
        return redirect('forum_post_detail', pk=pk)
        
    except ForumPost.DoesNotExist:
        error_msg = 'Post tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('forum_post_list')


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
        return redirect('forum_post_detail', pk=pk)
        
    except ForumPost.DoesNotExist:
        error_msg = 'Post tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('forum_post_list')


# ==================== USER-SPECIFIC VIEWS ====================

@login_required
def my_posts(request):
    """
    Menampilkan post milik user yang login dengan AJAX support
    """
    try:
        posts = ForumPost.objects.filter(
            author=request.user, 
            is_deleted=False
        ).select_related('category').order_by('-created_at')
        
        # AJAX request untuk data post user
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            posts_data = [_get_post_data(post) for post in posts]
            return JsonResponse({
                'status': 'success',
                'posts': posts_data
            })
        
        context = {
            'posts': posts,
            'title': 'Post Saya',
            'show_user_filter': False
        }
        return render(request, 'forum/post_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return redirect('forum_post_list')


@login_required
def my_pinned_posts(request):
    """
    Menampilkan post yang dipin (untuk admin) dengan AJAX support
    """
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, 'Hanya admin yang bisa mengakses halaman ini!')
        return redirect('forum_post_list')
    
    try:
        posts = ForumPost.get_pinned_posts().select_related('author', 'category')
        
        context = {
            'posts': posts,
            'title': 'Post yang Dipin',
            'show_pin_actions': True
        }
        return render(request, 'forum/post_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return redirect('forum_post_list')


# ==================== API VIEWS (JSON/XML) ====================

def show_forum_json(request):
    """Mengembalikan semua post forum dalam format JSON"""
    try:
        post_list = ForumPost.get_active_posts().select_related('author', 'category').order_by('-created_at')
        json_data = serializers.serialize("json", post_list)
        return HttpResponse(json_data, content_type="application/json")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_forum_xml(request):
    """Mengembalikan semua post forum dalam format XML"""
    try:
        post_list = ForumPost.get_active_posts().select_related('author', 'category').order_by('-created_at')
        xml_data = serializers.serialize("xml", post_list)
        return HttpResponse(xml_data, content_type="application/xml")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_forum_json_by_id(request, pk):
    """Mengembalikan post forum tertentu dalam format JSON"""
    try:
        post = ForumPost.objects.select_related('author', 'category').get(id=pk, is_deleted=False)
        json_data = serializers.serialize("json", [post])
        return HttpResponse(json_data, content_type="application/json")
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Post tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_forum_xml_by_id(request, pk):
    """Mengembalikan post forum tertentu dalam format XML"""
    try:
        post = ForumPost.objects.select_related('author', 'category').get(id=pk, is_deleted=False)
        xml_data = serializers.serialize("xml", [post])
        return HttpResponse(xml_data, content_type="application/xml")
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Post tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_forum_json_by_category(request, category_id):
    """Mengembalikan post forum berdasarkan kategori dalam format JSON"""
    try:
        post_list = ForumPost.objects.filter(
            category_id=category_id, 
            is_deleted=False
        ).select_related('author', 'category').order_by('-created_at')
        json_data = serializers.serialize("json", post_list)
        return HttpResponse(json_data, content_type="application/json")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)