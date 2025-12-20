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
import requests
from django.http import HttpResponse
import base64
from django.core.files.base import ContentFile
import mimetypes
import uuid

User = get_user_model()


def process_post_interaction(user, post, action, data=None):
    """Process a like/dislike/save/share/report action for a post.

    Returns a dict with keys similar to the JsonResponse payload used
    by the API view (e.g. status, message, action, likes_count, dislikes_count,
    user_interaction, is_saved, shares_count, report_id).
    """
    data = data or {}
    if action in ("like", "dislike"):
        try:
            interaction = PostInteraction.objects.get(user=user, post=post)

            # If same interaction, remove it (toggle off)
            if interaction.interaction_type == action:
                interaction.delete()
                return {
                    "status": "success",
                    "message": f"{action.capitalize()} removed",
                    "action": "removed",
                    "likes_count": post.likes_count,
                    "dislikes_count": post.dislikes_count,
                    "user_interaction": None,
                }
            else:
                # Change interaction type (like -> dislike or vice versa)
                interaction.interaction_type = action
                interaction.save()
                return {
                    "status": "success",
                    "message": f"Changed to {action}",
                    "action": "changed",
                    "likes_count": post.likes_count,
                    "dislikes_count": post.dislikes_count,
                    "user_interaction": action,
                }
        except PostInteraction.DoesNotExist:
            PostInteraction.objects.create(
                user=user, post=post, interaction_type=action
            )
            return {
                "status": "success",
                "message": f"Post {action}d",
                "action": "added",
                "likes_count": post.likes_count,
                "dislikes_count": post.dislikes_count,
                "user_interaction": action,
            }

    elif action == "save":
        existing_save = PostSave.objects.filter(user=user, post=post).first()
        if existing_save:
            existing_save.delete()
            return {
                "status": "success",
                "message": "Bookmark dihapus",
                "action": "removed",
                "is_saved": False,
            }
        PostSave.objects.create(user=user, post=post)
        return {
            "status": "success",
            "message": "Post disimpan",
            "action": "saved",
            "is_saved": True,
        }

    elif action == "share":
        PostShare.objects.create(user=user, post=post)
        return {
            "status": "success",
            "message": "Post berhasil dibagikan",
            "shares_count": post.shares_count,
        }

    elif action == "report":
        report = Report.objects.create(
            reporter=user,
            post=post,
            category=data.get("category", "OTHER"),
            description=data.get("description", ""),
        )
        return {
            "status": "success",
            "message": "Post berhasil dilaporkan",
            "report_id": report.id,
        }

    else:
        return {"status": "error", "message": "Action tidak valid"}


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
                url = (
                    profile.profile_photo.url
                    if profile and profile.profile_photo
                    else None
                )
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
                    user_interactions.get(post.id)
                    if request.user.is_authenticated
                    else None
                )
                is_saved = (
                    post.id in saved_post_ids
                    if request.user.is_authenticated
                    else False
                )

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
                    is_saved = (
                        post.id in saved_post_ids
                        if request.user.is_authenticated
                        else False
                    )

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

            # Handle base64 image data (from mobile clients)
            if not image_file and data.get("image_data"):
                try:
                    image_b64 = data.get("image_data")
                    image_name = data.get("image_name") or f"post_{post.id}.jpg"
                    file_data = base64.b64decode(image_b64)
                    post.image.save(image_name, ContentFile(file_data))
                    post.save()
                except Exception as e:
                    # If saving image fails, log and continue (post already created)
                    print(f"Failed to save base64 image: {e}")

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


@login_required(login_url="account:login_register")
def edit_post_page(request, post_id):
    post = get_object_or_404(Post, id=post_id, is_deleted=False)
    if not (post.user == request.user or request.user.is_superuser):
        return redirect("main:home")
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
            if request.user.is_superuser or request.user.has_perm(
                "post.manage_all_posts"
            ):
                post = Post.objects.get(id=post_id)
            else:
                post = Post.objects.get(id=post_id, is_deleted=False)
            data = json.loads(request.body) if request.body else {}

            # Delegate processing to reusable helper
            result = process_post_interaction(request.user, post, action, data)
            status_code = 200 if result.get("status") == "success" else 400
            return JsonResponse(result, status=status_code)

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
        is_superuser = request.user.is_superuser or request.user.has_perm(
            "post.manage_all_posts"
        )

        if not (is_owner or is_superuser):
            return redirect("post:index")

        context = {"post": post, "page_title": f"Edit Post - {post.title}"}

        return render(request, "edit_post.html", context)

    except Exception as e:
        print(f"Error in edit_post view: {e}")
        return redirect("post:index")


def proxy_image(request):
    image_url = request.GET.get("url")
    if not image_url:
        return HttpResponse("No URL provided", status=400)

    proxy_headers = {
        "User-Agent": "smash/1.0",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }

    # Resolve relative URLs to absolute (serve local media correctly)
    if image_url.startswith("/"):
        image_url = request.build_absolute_uri(image_url)
    elif not image_url.lower().startswith("http"):
        # Treat as relative path
        if not image_url.startswith("/"):
            image_url = f"/{image_url}"
        image_url = request.build_absolute_uri(image_url)

    try:
        # Fetch image from external source with a friendly UA to avoid 403s
        response = requests.get(image_url, timeout=10, headers=proxy_headers)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        # Fall back to inferring type for providers that omit the header
        if not content_type.startswith("image/"):
            guessed_type, _ = mimetypes.guess_type(image_url)
            if guessed_type and guessed_type.startswith("image/"):
                content_type = guessed_type
            else:
                payload = response.content
                if payload.startswith(b"\x89PNG\r\n\x1a\n"):
                    content_type = "image/png"
                elif payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
                    content_type = "image/webp"
                elif payload.startswith(b"\xff\xd8"):
                    content_type = "image/jpeg"
                elif payload.startswith(b"GIF87a") or payload.startswith(b"GIF89a"):
                    content_type = "image/gif"
                else:
                    content_type = "image/jpeg"

        resp = HttpResponse(
            response.content,
            content_type=content_type or "application/octet-stream",
        )
        # Helpful headers for clients (CORS for web use, caching)
        resp["Access-Control-Allow-Origin"] = "*"
        resp["Cache-Control"] = "max-age=3600, public"
        return resp
    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code if err.response else 502
        return HttpResponse(
            f"Upstream responded with {status_code}", status=status_code
        )
    except requests.RequestException as err:
        return HttpResponse(f"Error fetching image: {str(err)}", status=502)


@csrf_exempt
def create_post_flutter(request):
    """
    Endpoint to create a new post from a Flutter mobile app.
    Expects JSON payload with title, content, optional image and video_link.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method"}, status=401)

    try:
        # Accept JSON body or form-encoded data
        data = {}
        if request.body:
            try:
                data = json.loads(request.body)
            except Exception:
                data = request.POST.dict() if hasattr(request, "POST") else {}
        else:
            data = request.POST.dict() if hasattr(request, "POST") else {}

        title = data.get("title")
        content = data.get("content")
        image_data = data.get("image") or data.get("image_data")
        video_link = data.get("video_link", "")

        # Prefer authenticated user; fall back to provided user_id in payload
        user = None
        if getattr(request, "user", None) and request.user.is_authenticated:
            user = request.user
        else:
            provided_user_id = data.get("user_id") or data.get("userId")
            if provided_user_id:
                try:
                    user = User.objects.get(id=int(provided_user_id))
                except (User.DoesNotExist, ValueError):
                    return JsonResponse(
                        {"error": "User not found (provided user_id invalid)"},
                        status=400,
                    )

        if user is None:
            return JsonResponse(
                {"error": "Authentication required or provide user_id in payload"},
                status=401,
            )

        new_post = Post(user=user, title=title, content=content, video_link=video_link)

        # Handle base64 image data if provided
        if image_data:
            try:
                # If data URI like 'data:image/png;base64,...', split header
                if isinstance(image_data, str) and image_data.startswith("data:"):
                    header, encoded = image_data.split(",", 1)
                    try:
                        mime = header.split(";")[0].split(":")[1]
                    except Exception:
                        mime = None
                else:
                    encoded = image_data
                    mime = None

                decoded = base64.b64decode(encoded)

                # Basic size and type checks
                MAX_IMAGE_BYTES = 5 * 1024 * 1024
                if len(decoded) > MAX_IMAGE_BYTES:
                    return JsonResponse(
                        {"error": "Image too large (max 5MB)"}, status=400
                    )

                detected_mime = mime
                if not detected_mime:

                    def _detect_mime(data: bytes) -> str | None:
                        if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
                            return "image/png"
                        if len(data) >= 2 and data[0:2] == b"\xff\xd8":
                            return "image/jpeg"
                        if len(data) >= 6 and (
                            data[:6] == b"GIF87a" or data[:6] == b"GIF89a"
                        ):
                            return "image/gif"
                        if (
                            len(data) >= 12
                            and data[0:4] == b"RIFF"
                            and data[8:12] == b"WEBP"
                        ):
                            return "image/webp"
                        return None

                    detected_mime = _detect_mime(decoded)

                ALLOWED_MIME = {
                    "image/png",
                    "image/jpeg",
                    "image/jpg",
                    "image/webp",
                    "image/gif",
                }
                if not detected_mime or detected_mime.lower() not in ALLOWED_MIME:
                    return JsonResponse({"error": "Unsupported image type"}, status=400)

                ext = detected_mime.split("/")[-1]
                filename = f"post_{uuid.uuid4().hex[:12]}.{ext}"
                new_post.image.save(filename, ContentFile(decoded), save=False)
            except base64.binascii.Error:
                return JsonResponse({"error": "Invalid base64 image data"}, status=400)
            except Exception as ie:
                return JsonResponse({"error": f"Invalid image data: {ie}"}, status=400)

        new_post.save()

        return JsonResponse(
            {"message": "Post created successfully", "post_id": str(new_post.id)},
            status=201,
        )
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def get_comments(request, post_id):
    """
    Returns comments for a specific post as JSON suitable for consumption by a
    mobile app (e.g. Flutter). Each comment includes id, content, author,
    timestamps.
    """
    try:
        p = Post.objects.get(id=post_id, is_deleted=False)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    # Order by newest first for mobile clients
    comments_qs = p.comments.filter(is_deleted=False).order_by("-created_at")
    comments_list = []
    user_id = request.GET.get("user_id")
    for c in comments_qs:
        user_reaction = None
        if user_id:
            try:
                u = User.objects.get(id=user_id)
                try:
                    ci = CommentInteraction.objects.get(user=u, comment=c)
                    user_reaction = ci.interaction_type
                except CommentInteraction.DoesNotExist:
                    user_reaction = None
            except User.DoesNotExist:
                user_reaction = None

        comments_list.append(
            {
                "id": c.id,
                "content": c.content,
                "author": getattr(c.user, "username", None),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "likes_count": c.likes_count,
                "dislikes_count": c.dislikes_count,
                "user_reaction": user_reaction,
            }
        )

    return JsonResponse(comments_list, safe=False)


@csrf_exempt
def create_comment_flutter(request):
    """
    Endpoint to create a new comment from Flutter.
    Expects JSON payload: post_id, content, user_id, optional parent_id
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method"}, status=401)

    try:
        # Accept either JSON body or form-encoded POST data for compatibility
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            # Fallback to form data (Content-Type: application/x-www-form-urlencoded)
            data = {
                "post_id": request.POST.get("post_id") or request.POST.get("postId"),
                "content": request.POST.get("content"),
                "user_id": request.POST.get("user_id") or request.POST.get("userId"),
                "parent_id": request.POST.get("parent_id")
                or request.POST.get("parentId"),
            }

        post_id = data.get("post_id")
        content = data.get("content")
        user_id = data.get("user_id")
        parent_id = data.get("parent_id")

        if not post_id or not content or not user_id:
            return JsonResponse({"error": "Missing fields"}, status=400)

        p = Post.objects.get(id=post_id, is_deleted=False)
        user = User.objects.get(id=user_id)

        comment = Comment(user=user, post=p, content=content)
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
                comment.parent = parent
            except Comment.DoesNotExist:
                pass

        comment.save()
        return JsonResponse(
            {
                "status": "success",
                "message": "Comment created",
                "comment": {
                    "id": comment.id,
                    "content": comment.content,
                    "author": getattr(comment.user, "username", None),
                    "created_at": comment.created_at.isoformat(),
                },
            },
            status=201,
        )
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
