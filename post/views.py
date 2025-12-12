# post/views.py
import json
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Post, PostInteraction, PostSave, PostShare
from comment.models import Comment, CommentInteraction
from report.models import Report
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from profil.models import Profile

User = get_user_model()

class PostAPIView(View):
    """
    API View untuk handling CRUD operations pada Post.
    Mendukung AJAX requests dan superuser permissions.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch untuk handle AJAX requests"""
        return super().dispatch(request, *args, **kwargs)

    def get_user_permissions(self, user, post=None):
        """Helper method untuk check user permissions"""
        is_owner = post and post.user == user if post else False
        is_superuser = user.is_superuser or user.has_perm("post.manage_all_posts")
        return is_owner, is_superuser

    def get(self, request, post_id=None):
        """
        GET: Retrieve single post atau list of posts
        AJAX Support: ✅
        """
        try:
            user_interactions = {}
            saved_post_ids = set()
            profile_cache = {}

            def get_profile_photo_url(user):
                if user.id in profile_cache:
                    return profile_cache[user.id]
                profile = Profile.objects.filter(user=user).first()
                url = profile.profile_photo.url if profile and profile.profile_photo else None
                profile_cache[user.id] = url
                return url

            if request.user.is_authenticated:
                user_interactions = dict(
                    PostInteraction.objects.filter(user=request.user).values_list(
                        "post_id", "interaction_type"
                    )
                )
                saved_post_ids = set(
                    PostSave.objects.filter(user=request.user).values_list(
                        "post_id", flat=True
                    )
                )
            if post_id:
                # Get single post
                post = Post.objects.get(id=post_id, is_deleted=False)

                # Check jika user memiliki akses
                if (
                    post.is_deleted
                    and not self.get_user_permissions(request.user, post)[1]
                ):
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Post tidak ditemukan atau telah dihapus",
                        },
                        status=404,
                    )

                # Get user interaction if authenticated
                user_interaction = (
                    user_interactions.get(post.id) if request.user.is_authenticated else None
                )
                is_saved = post.id in saved_post_ids if request.user.is_authenticated else False

                post_data = {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "image": post.image.url if post.image else None,
                    "video_link": post.video_link,
                    "user": post.user.username,
                    "user_id": post.user.id,
                    "created_at": post.created_at.isoformat(),
                    "updated_at": post.updated_at.isoformat(),
                    "comment_count": post.comments.filter(is_deleted=False).count(),
                    "likes_count": post.likes_count,
                    "dislikes_count": post.dislikes_count,
                    "shares_count": post.shares_count,
                    "profile_photo": get_profile_photo_url(post.user),
                    "user_interaction": user_interaction,
                    "is_saved": is_saved,
                    "can_edit": self.get_user_permissions(request.user, post)[0]
                    or self.get_user_permissions(request.user, post)[1],
                }

                return JsonResponse({"status": "success", "post": post_data})

            else:
                # Get list of posts dengan pagination
                page = int(request.GET.get("page", 1))
                per_page = int(request.GET.get("per_page", 10))
                start = (page - 1) * per_page
                end = start + per_page

                # Filter posts (superuser bisa lihat semua, user biasa hanya yang tidak deleted)
                if (
                    request.user.is_authenticated
                    and self.get_user_permissions(request.user)[1]
                ):
                    posts = Post.objects.all()
                else:
                    posts = Post.objects.filter(is_deleted=False)

                filter_by = request.GET.get("filter")
                if filter_by:
                    if not request.user.is_authenticated:
                        posts = Post.objects.none()
                    elif filter_by == "my":
                        posts = posts.filter(user=request.user)
                    elif filter_by == "bookmarked":
                        posts = posts.filter(id__in=saved_post_ids)
                    elif filter_by == "liked":
                        liked_post_ids = [
                            post_id
                            for post_id, action in user_interactions.items()
                            if action == "like"
                        ]
                        posts = posts.filter(id__in=liked_post_ids)

                # Apply ordering
                sort_by = request.GET.get("sort_by", "-created_at")
                posts = posts.order_by(sort_by)

                posts_data = []
                for post in posts[start:end]:
                    user_interaction = (
                        user_interactions.get(post.id)
                        if request.user.is_authenticated
                        else None
                    )
                    is_saved = post.id in saved_post_ids if request.user.is_authenticated else False

                    posts_data.append(
                        {
                            "id": post.id,
                            "title": post.title,
                            "content": post.content,
                            "image": post.image.url if post.image else None,
                            "video_link": post.video_link,
                            "user": post.user.username,
                            "user_id": post.user.id,
                            "created_at": post.created_at.isoformat(),
                            "profile_photo": get_profile_photo_url(post.user),
                            "comment_count": post.comments.filter(
                                is_deleted=False
                            ).count(),
                            "likes_count": post.likes_count,
                            "dislikes_count": post.dislikes_count,
                            "shares_count": post.shares_count,
                            "user_interaction": user_interaction,
                            "is_saved": is_saved,
                            "can_edit": self.get_user_permissions(request.user, post)[0]
                            or self.get_user_permissions(request.user, post)[1],
                        }
                    )

                return JsonResponse(
                    {
                        "status": "success",
                        "posts": posts_data,
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": posts.count(),
                            "has_next": end < posts.count(),
                        },
                    }
                )

        except Post.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Post tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error retrieving post: {str(e)}"},
                status=500,
            )

    @method_decorator(require_http_methods(["POST"]))
    def post(self, request):
        """
        POST: Create new post
        AJAX Support: ✅
        Mendukung FormData untuk file upload
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            # Handle FormData (check for multipart or if FILES exist)
            if request.FILES or (
                hasattr(request, "content_type")
                and request.content_type
                and "multipart/form-data" in request.content_type
            ):
                # Parse JSON data from FormData
                data_str = request.POST.get("data", "{}")
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    # If no JSON data, try to get individual fields
                    data = {
                        "title": request.POST.get("title", ""),
                        "content": request.POST.get("content", ""),
                        "video_link": request.POST.get("video_link", ""),
                    }

                # Get file
                image_file = request.FILES.get("image")
            else:
                # Handle regular JSON
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid JSON format"},
                        status=400,
                    )
                image_file = None

            # Validasi required fields
            required_fields = ["title", "content"]
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse(
                        {"status": "error", "message": f"Field {field} harus diisi"},
                        status=400,
                    )

            # Create post
            post = Post.objects.create(
                user=request.user,
                title=data["title"],
                content=data["content"],
                video_link=data.get("video_link", ""),
            )

            # Handle image upload jika ada
            if image_file:
                # Validasi file type
                allowed_types = ["image/jpeg", "image/png", "image/gif"]
                if image_file.content_type not in allowed_types:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "File type tidak didukung. Gunakan JPG, PNG, atau GIF.",
                        },
                        status=400,
                    )

                # Validasi file size (max 5MB)
                if image_file.size > 5 * 1024 * 1024:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Ukuran file terlalu besar. Maksimal 5MB.",
                        },
                        status=400,
                    )

                post.image = image_file
                post.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Post berhasil dibuat",
                    "post_id": post.id,
                    "post": {
                        "id": post.id,
                        "title": post.title,
                        "content": post.content,
                        "image": post.image.url if post.image else None,
                        "video_link": post.video_link,
                        "user": post.user.username,
                        "created_at": post.created_at.isoformat(),
                        "comment_count": 0,
                        "shares_count": 0,
                        "can_edit": True,
                    },
                },
                status=201,
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON format"}, status=400
            )
        except ValidationError as e:
            return JsonResponse(
                {"status": "error", "message": f"Validation error: {str(e)}"},
                status=400,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()  # Print full error to console for debugging
            return JsonResponse(
                {"status": "error", "message": f"Error creating post: {str(e)}"},
                status=500,
            )

    @method_decorator(require_http_methods(["PUT"]))
    def put(self, request, post_id):
        """
        PUT: Update existing post
        AJAX Support: ✅
        Mendukung FormData untuk file upload
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            post = Post.objects.get(id=post_id)
            is_owner, is_superuser = self.get_user_permissions(request.user, post)

            if not (is_owner or is_superuser):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Anda tidak memiliki izin untuk mengedit post ini",
                    },
                    status=403,
                )

            data = {}
            image_file = None

            # Support multipart/form-data for PUT (manual parsing)
            try:
                if (
                    hasattr(request, "content_type")
                    and request.content_type
                    and "multipart/form-data" in request.content_type
                ):
                    parser = MultiPartParser(
                        request.META, request, request.upload_handlers, request.encoding
                    )
                    data_qd, files = parser.parse()
                    data = data_qd
                    image_file = files.get("image")
                else:
                    # JSON body fallback
                    data = json.loads(request.body) if request.body else {}
            except (MultiPartParserError, json.JSONDecodeError):
                return JsonResponse(
                    {"status": "error", "message": "Invalid request format"},
                    status=400,
                )

            # Update fields (accept both QueryDict and dict)
            for field in ["title", "content", "video_link"]:
                if field in data and data.get(field) is not None:
                    setattr(post, field, data.get(field))

            # Handle remove image flag
            remove_image_val = str(data.get("remove_image", "")).lower()
            if remove_image_val in ("true", "1", "on", "yes"):
                post.image = None

            # Handle image update with basic validation
            if not image_file and hasattr(request, "FILES"):
                image_file = request.FILES.get("image")

            if image_file:
                allowed_types = ["image/jpeg", "image/png", "image/gif"]
                if getattr(image_file, "content_type", "") not in allowed_types:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "File type tidak didukung. Gunakan JPG, PNG, atau GIF.",
                        },
                        status=400,
                    )

                if getattr(image_file, "size", 0) > 5 * 1024 * 1024:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "Ukuran file terlalu besar. Maksimal 5MB.",
                        },
                        status=400,
                    )

                post.image = image_file

            post.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Post berhasil diupdate",
                    "post_id": post.id,
                    "post": {
                        "id": post.id,
                        "title": post.title,
                        "content": post.content,
                        "image": post.image.url if post.image else None,
                        "video_link": post.video_link,
                        "updated_at": post.updated_at.isoformat(),
                    },
                }
            )

        except Post.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Post tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error updating post: {str(e)}"},
                status=500,
            )

    @method_decorator(require_http_methods(["DELETE"]))
    def delete(self, request, post_id):
        """
        DELETE: Soft delete post
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            post = Post.objects.get(id=post_id)
            is_owner, is_superuser = self.get_user_permissions(request.user, post)

            if not (is_owner or is_superuser):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Anda tidak memiliki izin untuk menghapus post ini",
                    },
                    status=403,
                )

            # Soft delete
            post.delete()

            return JsonResponse(
                {"status": "success", "message": "Post berhasil dihapus"}
            )

        except Post.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Post tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error deleting post: {str(e)}"},
                status=500,
            )


@login_required(login_url='account:login_register')
def edit_post_page(request, post_id):
    post = get_object_or_404(Post, id=post_id, is_deleted=False)
    if not (post.user == request.user or request.user.is_superuser):
        return redirect('main:home')
    context = {
        "post": post,
        "page_title": "Edit Post",
    }
    return render(request, "edit_post.html", context)

class PostInteractionView(View):
    """
    View untuk handling post interactions (like, save, share, report)
    Mendukung AJAX requests.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(require_http_methods(["POST"]))
    def post(self, request, post_id, action):
        """
        POST: Handle post interactions (like, save, share, report)
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            # Superuser can interact with any post (even if soft-deleted)
            if request.user.is_superuser or request.user.has_perm("post.manage_all_posts"):
                post = Post.objects.get(id=post_id)
            else:
                post = Post.objects.get(id=post_id, is_deleted=False)
            data = json.loads(request.body) if request.body else {}

            if action == "like" or action == "dislike":
                # Handle like/dislike action
                try:
                    interaction = PostInteraction.objects.get(
                        user=request.user, post=post
                    )

                    # If same interaction, remove it (toggle off)
                    if interaction.interaction_type == action:
                        interaction.delete()
                        return JsonResponse(
                            {
                                "status": "success",
                                "message": f"{action.capitalize()} removed",
                                "action": "removed",
                                "likes_count": post.likes_count,
                                "dislikes_count": post.dislikes_count,
                                "user_interaction": None,
                            }
                        )
                    else:
                        # Change interaction type (like to dislike or vice versa)
                        interaction.interaction_type = action
                        interaction.save()
                        return JsonResponse(
                            {
                                "status": "success",
                                "message": f"Changed to {action}",
                                "action": "changed",
                                "likes_count": post.likes_count,
                                "dislikes_count": post.dislikes_count,
                                "user_interaction": action,
                            }
                        )
                except PostInteraction.DoesNotExist:
                    # Create new interaction
                    PostInteraction.objects.create(
                        user=request.user, post=post, interaction_type=action
                    )
                    return JsonResponse(
                        {
                            "status": "success",
                            "message": f"Post {action}d",
                            "action": "added",
                            "likes_count": post.likes_count,
                            "dislikes_count": post.dislikes_count,
                            "user_interaction": action,
                        }
                    )

            elif action == "report":
                # Handle report action
                report = Report.objects.create(
                    reporter=request.user,
                    post=post,
                    category=data.get("category", "OTHER"),
                    description=data.get("description", ""),
                )

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Post berhasil dilaporkan",
                        "report_id": report.id,
                    }
                )

            elif action == "save":
                existing_save = PostSave.objects.filter(user=request.user, post=post).first()
                if existing_save:
                    existing_save.delete()
                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "Bookmark dihapus",
                            "action": "removed",
                            "is_saved": False,
                        }
                    )

                PostSave.objects.create(user=request.user, post=post)
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Post disimpan",
                        "action": "saved",
                        "is_saved": True,
                    }
                )

            elif action == "share":
                # Handle share action - track each share
                PostShare.objects.create(user=request.user, post=post)

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Post berhasil dibagikan",
                        "shares_count": post.shares_count,
                    }
                )

            else:
                return JsonResponse(
                    {"status": "error", "message": "Action tidak valid"}, status=400
                )

        except Post.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Post tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error processing action: {str(e)}"},
                status=500,
            )


# TAMBAH FUNGSI UNTUK SEARCH POST
def hot_threads(request):
    """
    Menampilkan thread terpopuler berdasarkan jumlah like + komentar
    """
    posts = (
        Post.objects.filter(is_deleted=False)
        .annotate(
            likes_count=Count(
                "interactions", filter=Q(interactions__interaction_type="like")
            ),
            comments_count=Count("comments"),
        )
        .annotate(
            total_score=Count(
                "interactions", filter=Q(interactions__interaction_type="like")
            )
            + Count("comments")
        )
        .order_by("-total_score", "-created_at")[:50]
    )

    return render(
        request, "post/hot_threads.html", {"posts": posts, "page_title": "Hot Threads"}
    )


@login_required
def bookmarked_threads(request):
    """
    Menampilkan postingan yang telah disimpan oleh pengguna (bookmark)
    """
    saves = (
        PostSave.objects.filter(user=request.user)
        .select_related("post")
        .order_by("-created_at")
    )
    posts = [s.post for s in saves if not s.post.is_deleted]

    return render(
        request,
        "post/bookmarked_threads.html",
        {"posts": posts, "page_title": "Bookmarks"},
    )


def recent_thread(request):
    posts = Post.objects.filter(is_deleted=False).order_by("-created_at")[:50]
    return render(
        request,
        "post/recent_threads.html",
        {"posts": posts, "page_title": "Recent Threads"},
    )


@login_required
def edit_post(request, post_id):
    """
    View untuk halaman edit post
    """
    try:
        post = get_object_or_404(Post, id=post_id, is_deleted=False)
        
        # Check permissions
        is_owner = post.user == request.user
        is_superuser = request.user.is_superuser or request.user.has_perm("post.manage_all_posts")
        
        if not (is_owner or is_superuser):
            return redirect('post:index')
        
        context = {
            'post': post,
            'page_title': f'Edit Post - {post.title}'
        }
        
        return render(request, 'edit_post.html', context)
        
    except Exception as e:
        print(f"Error in edit_post view: {e}")
        return redirect('post:index')
