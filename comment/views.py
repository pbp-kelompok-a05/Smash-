# comment/views.py
import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Comment, CommentInteraction
from post.models import Post
from report.models import Report

User = get_user_model()


class CommentAPIView(View):
    """
    API View untuk handling CRUD operations pada Comment.
    Mendukung AJAX requests dan nested comments.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_user_permissions(self, user, comment=None):
        """Helper method untuk check user permissions"""
        is_owner = comment and comment.user == user if comment else False
        is_superuser = user.is_superuser or user.has_perm("comment.manage_all_comments")
        return is_owner, is_superuser

    def get(self, request, post_id=None, comment_id=None):
        """
        GET: Retrieve comments untuk post atau single comment
        AJAX Support: ✅
        """
        try:
            if comment_id:
                # Get single comment
                comment = Comment.objects.get(id=comment_id, is_deleted=False)

                comment_data = {
                    "id": comment.id,
                    "content": comment.content,
                    "emoji": comment.emoji,
                    "user": comment.user.username,
                    "user_id": comment.user.id,
                    "post_id": comment.post.id,
                    "parent_id": comment.parent.id if comment.parent else None,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat(),
                    "likes_count": comment.likes_count,
                    "is_reply": comment.is_reply,
                    "can_edit": self.get_user_permissions(request.user, comment)[0]
                    or self.get_user_permissions(request.user, comment)[1],
                    "replies": [],
                }

                # Include replies jika ada
                if comment.replies.filter(is_deleted=False).exists():
                    for reply in comment.replies.filter(is_deleted=False):
                        comment_data["replies"].append(
                            {
                                "id": reply.id,
                                "content": reply.content,
                                "user": reply.user.username,
                                "created_at": reply.created_at.isoformat(),
                            }
                        )

                return JsonResponse({"status": "success", "comment": comment_data})

            elif post_id:
                # Get all comments untuk post tertentu
                post = Post.objects.get(id=post_id, is_deleted=False)

                # Filter dan ordering
                sort_by = request.GET.get("sort_by", "-created_at")
                comments = Comment.objects.filter(
                    post=post,
                    is_deleted=False,
                    parent__isnull=True,  # Hanya parent comments
                ).order_by(sort_by)

                comments_data = []
                for comment in comments:
                    # Get user's interaction with this comment
                    user_interaction = None
                    if request.user.is_authenticated:
                        try:
                            interaction = CommentInteraction.objects.get(
                                user=request.user, comment=comment
                            )
                            user_interaction = interaction.interaction_type
                        except CommentInteraction.DoesNotExist:
                            pass

                    comment_data = {
                        "id": comment.id,
                        "content": comment.content,
                        "emoji": comment.emoji,
                        "user": comment.user.username,
                        "user_id": comment.user.id,
                        "created_at": comment.created_at.isoformat(),
                        "updated_at": comment.updated_at.isoformat(),
                        "likes_count": comment.likes_count,
                        "dislikes_count": comment.dislikes_count,
                        "user_interaction": user_interaction,
                        "can_edit": self.get_user_permissions(request.user, comment)[0]
                        or self.get_user_permissions(request.user, comment)[1],
                        "replies": [],
                    }

                    # Include replies
                    replies = comment.replies.filter(is_deleted=False).order_by(
                        "created_at"
                    )
                    for reply in replies:
                        comment_data["replies"].append(
                            {
                                "id": reply.id,
                                "content": reply.content,
                                "user": reply.user.username,
                                "user_id": reply.user.id,
                                "created_at": reply.created_at.isoformat(),
                                "can_edit": self.get_user_permissions(
                                    request.user, reply
                                )[0]
                                or self.get_user_permissions(request.user, reply)[1],
                            }
                        )

                    comments_data.append(comment_data)

                return JsonResponse(
                    {
                        "status": "success",
                        "comments": comments_data,
                        "total_comments": comments.count(),
                    }
                )

            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Post ID atau Comment ID diperlukan",
                    },
                    status=400,
                )

        except (Post.DoesNotExist, Comment.DoesNotExist):
            return JsonResponse(
                {"status": "error", "message": "Post atau komentar tidak ditemukan"},
                status=404,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error retrieving comments: {str(e)}"},
                status=500,
            )

    def post(self, request, post_id=None, comment_id=None):
        """
        POST: Create new comment atau reply
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            if not post_id:
                return JsonResponse(
                    {"status": "error", "message": "Post ID is required"},
                    status=400,
                )

            post = Post.objects.get(id=post_id, is_deleted=False)
            data = json.loads(request.body)

            # Validasi required fields
            if not data.get("content") and not data.get("emoji"):
                return JsonResponse(
                    {"status": "error", "message": "Konten atau emoji harus diisi"},
                    status=400,
                )

            # Create comment
            comment_data = {
                "user": request.user,
                "post": post,
                "content": data.get("content", ""),
                "emoji": data.get("emoji", ""),
            }

            # Handle nested comments (replies)
            parent_id = data.get("parent_id")
            if parent_id:
                parent_comment = Comment.objects.get(id=parent_id, is_deleted=False)
                comment_data["parent"] = parent_comment

            comment = Comment.objects.create(**comment_data)

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Komentar berhasil dibuat",
                    "comment_id": comment.id,
                },
                status=201,
            )

        except Post.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Post tidak ditemukan"}, status=404
            )
        except Comment.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Komentar induk tidak ditemukan"},
                status=404,
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error creating comment: {str(e)}"},
                status=500,
            )

    def put(self, request, post_id=None, comment_id=None):
        """
        PUT: Update existing comment
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            if not comment_id:
                return JsonResponse(
                    {"status": "error", "message": "Comment ID is required"},
                    status=400,
                )

            comment = Comment.objects.get(id=comment_id)
            is_owner, is_superuser = self.get_user_permissions(request.user, comment)

            if not (is_owner or is_superuser):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Anda tidak memiliki izin untuk mengedit komentar ini",
                    },
                    status=403,
                )

            data = json.loads(request.body)

            # Update fields
            if "content" in data:
                comment.content = data["content"]
            if "emoji" in data:
                comment.emoji = data["emoji"]

            comment.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Komentar berhasil diupdate",
                    "comment_id": comment.id,
                }
            )

        except Comment.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Komentar tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error updating comment: {str(e)}"},
                status=500,
            )

    def delete(self, request, post_id=None, comment_id=None):
        """
        DELETE: Soft delete comment
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            if not comment_id:
                return JsonResponse(
                    {"status": "error", "message": "Comment ID is required"},
                    status=400,
                )

            comment = Comment.objects.get(id=comment_id)
            is_owner, is_superuser = self.get_user_permissions(request.user, comment)

            if not (is_owner or is_superuser):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Anda tidak memiliki izin untuk menghapus komentar ini",
                    },
                    status=403,
                )

            # Soft delete
            comment.delete()

            return JsonResponse(
                {"status": "success", "message": "Komentar berhasil dihapus"}
            )

        except Comment.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Komentar tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error deleting comment: {str(e)}"},
                status=500,
            )


class CommentInteractionView(View):
    """
    View untuk handling comment interactions (like, dislike, report)
    Mendukung AJAX requests.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(require_http_methods(["POST"]))
    def post(self, request, comment_id, action):
        """
        POST: Handle comment interactions
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse(
                    {"status": "error", "message": "Authentication required"},
                    status=401,
                )

            comment = Comment.objects.get(id=comment_id, is_deleted=False)
            data = json.loads(request.body) if request.body else {}

            if action == "like":
                # Check if user already has an interaction with this comment
                interaction, created = CommentInteraction.objects.get_or_create(
                    user=request.user,
                    comment=comment,
                    defaults={"interaction_type": "like"},
                )

                if not created:
                    # User already interacted with this comment
                    if interaction.interaction_type == "like":
                        # Unlike: remove the interaction
                        interaction.delete()
                        comment.likes_count = max(0, comment.likes_count - 1)
                        comment.save()

                        return JsonResponse(
                            {
                                "status": "success",
                                "message": "Like removed",
                                "action": "unliked",
                                "likes_count": comment.likes_count,
                                "dislikes_count": comment.dislikes_count,
                            }
                        )
                    else:
                        # User had disliked, now switching to like
                        interaction.interaction_type = "like"
                        interaction.save()
                        comment.dislikes_count = max(0, comment.dislikes_count - 1)
                        comment.likes_count += 1
                        comment.save()

                        return JsonResponse(
                            {
                                "status": "success",
                                "message": "Changed to like",
                                "action": "liked",
                                "likes_count": comment.likes_count,
                                "dislikes_count": comment.dislikes_count,
                            }
                        )
                else:
                    # New like
                    comment.likes_count += 1
                    comment.save()

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "Komentar berhasil disukai",
                            "action": "liked",
                            "likes_count": comment.likes_count,
                            "dislikes_count": comment.dislikes_count,
                        }
                    )

            elif action == "dislike":
                # Check if user already has an interaction with this comment
                interaction, created = CommentInteraction.objects.get_or_create(
                    user=request.user,
                    comment=comment,
                    defaults={"interaction_type": "dislike"},
                )

                if not created:
                    # User already interacted with this comment
                    if interaction.interaction_type == "dislike":
                        # Undislike: remove the interaction
                        interaction.delete()
                        comment.dislikes_count = max(0, comment.dislikes_count - 1)
                        comment.save()

                        return JsonResponse(
                            {
                                "status": "success",
                                "message": "Dislike removed",
                                "action": "undisliked",
                                "likes_count": comment.likes_count,
                                "dislikes_count": comment.dislikes_count,
                            }
                        )
                    else:
                        # User had liked, now switching to dislike
                        interaction.interaction_type = "dislike"
                        interaction.save()
                        comment.likes_count = max(0, comment.likes_count - 1)
                        comment.dislikes_count += 1
                        comment.save()

                        return JsonResponse(
                            {
                                "status": "success",
                                "message": "Changed to dislike",
                                "action": "disliked",
                                "likes_count": comment.likes_count,
                                "dislikes_count": comment.dislikes_count,
                            }
                        )
                else:
                    # New dislike
                    comment.dislikes_count += 1
                    comment.save()

                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "Komentar berhasil di-dislike",
                            "action": "disliked",
                            "likes_count": comment.likes_count,
                            "dislikes_count": comment.dislikes_count,
                        }
                    )

            elif action == "report":
                # Handle report action
                report = Report.objects.create(
                    reporter=request.user,
                    comment=comment,
                    category=data.get("category", "OTHER"),
                    description=data.get("description", ""),
                )

                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Komentar berhasil dilaporkan",
                        "report_id": report.id,
                    }
                )

            else:
                return JsonResponse(
                    {"status": "error", "message": "Action tidak valid"}, status=400
                )

        except Comment.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Komentar tidak ditemukan"}, status=404
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Error processing action: {str(e)}"},
                status=500,
            )
def show_json(request):
    comment_list= Comment.objects.all()
    interaction_list=CommentInteraction.objects.all()
    comments_data=[
        {
            'id': str(comment.id),
            'post_id': comment.post.id,
            'parent_id': comment.parent.id,
            'user_id': comment.user_id,
            'content': comment.content,
            'emoji':comment.emoji,
            'created_at': comment.created_at.isoformat() if comment.created_at else None,
            'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
            'is_deleted': comment.is_deleted,
            "likes_count": comment.likes_count,
            "dislikes_count": comment.dislikes_count,
        }
        for comment in comment_list
    ]
    interaction_data= [
        {
            'comment_id': str(interaction.comment.id),
            'user_id': interaction.user_id,
            'interaction_type': interaction.interaction_type,
            'created_at': interaction.created_at.isoformat() if interaction.created_at else None,
        }
        for interaction in interaction_list
    ]
    
