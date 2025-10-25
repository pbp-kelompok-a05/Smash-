# post/views.py
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from .models import Post, PostInteraction
from comment.models import Comment
from report.models import Report
from django.contrib.auth.decorators import login_required

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
                user_interaction = None
                if request.user.is_authenticated:
                    try:
                        interaction = PostInteraction.objects.get(
                            user=request.user, post=post
                        )
                        user_interaction = interaction.interaction_type
                    except PostInteraction.DoesNotExist:
                        pass

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
                    "user_interaction": user_interaction,
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

                # Apply ordering
                sort_by = request.GET.get("sort_by", "-created_at")
                posts = posts.order_by(sort_by)

                posts_data = []
                for post in posts[start:end]:
                    # Get user interaction if authenticated
                    user_interaction = None
                    if request.user.is_authenticated:
                        try:
                            interaction = PostInteraction.objects.get(
                                user=request.user, post=post
                            )
                            user_interaction = interaction.interaction_type
                        except PostInteraction.DoesNotExist:
                            pass

                    posts_data.append(
                        {
                            "id": post.id,
                            "title": post.title,
                            "content": post.content,
                            "image": post.image.url if post.image else None,
                            "video_link": post.video_link,
                            "user": post.user.username,
                            "created_at": post.created_at.isoformat(),
                            "comment_count": post.comments.filter(
                                is_deleted=False
                            ).count(),
                            "likes_count": post.likes_count,
                            "dislikes_count": post.dislikes_count,
                            "user_interaction": user_interaction,
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

            # Handle FormData
            if request.content_type == "multipart/form-data":
                # Parse JSON data from FormData
                data_str = request.POST.get("data", "{}")
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = {}

                # Get file
                image_file = request.FILES.get("image")
            else:
                # Handle regular JSON
                data = json.loads(request.body)
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
                        "can_edit": True,
                    },
                },
                status=201,
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Invalid JSON format"}, status=400
            )
        except Exception as e:
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

            data = json.loads(request.body)

            # Update fields
            update_fields = ["title", "content", "video_link"]
            for field in update_fields:
                if field in data:
                    setattr(post, field, data[field])

            # Handle image update
            if request.FILES.get("image"):
                post.image = request.FILES["image"]

            post.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Post berhasil diupdate",
                    "post_id": post.id,
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


class PostInteractionView(View):
    """
    View untuk handling post interactions (like, share, report)
    Mendukung AJAX requests.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(require_http_methods(["POST"]))
    def post(self, request, post_id, action):
        """
        POST: Handle post interactions (like, share, report)
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

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

            elif action == "share":
                # Handle share action (simulasi)
                share_count = data.get("share_count", 0) + 1

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Post berhasil dibagikan",
                        "share_count": share_count,
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
