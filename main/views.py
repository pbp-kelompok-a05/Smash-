# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.base import ContentFile
import base64
import uuid
from post.models import Post, User
from ads.models import Advertisement
from comment.models import Comment
import json


def home(request):
    """
    Homepage view yang menampilkan daftar post
    Accessible to all users (authenticated and anonymous)
    """
    # Tambahkan context jika perlu
    posts = Post.objects.all().order_by("-created_at")
    popup_ad = (
        Advertisement.objects.filter(
            ad_type="popup", is_active=True, image__isnull=False
        )
        .order_by("-created_at")
        .first()
    )
    return render(request, "main.html", {"posts": posts, "popup_ad": popup_ad})


def about_smash(request):
    """
    Halaman 'Tentang Smash' — berisi deskripsi website Smash!
    """
    return render(request, "about_smash.html")


def json_posts(request):
    """
    Returns all non-deleted posts as JSON suitable for consumption by a
    mobile app (e.g. Flutter). Fields include id, title, content, author,
    image/video links, timestamps and simple interaction counts.
    """
    posts_qs = Post.objects.filter(is_deleted=False).order_by("-created_at")
    posts_list = []
    for p in posts_qs:
        image_url = None
        if p.image:
            try:
                image_url = request.build_absolute_uri(p.image.url)
            except Exception:
                # Fallback to relative URL if building absolute fails
                image_url = getattr(p.image, "url", None)

        posts_list.append(
            {
                "id": str(p.id),
                "title": p.title,
                "content": p.content,
                "author": getattr(p.user, "username", None),
                "image_url": image_url,
                "video_link": p.video_link,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "likes_count": p.likes_count,
                "dislikes_count": p.dislikes_count,
                "shares_count": p.shares_count,
                "is_deleted": p.is_deleted,
            }
        )

    return JsonResponse(posts_list, safe=False)


def json_post_id(request, post_id):
    """
    Returns a single post by ID as JSON suitable for consumption by a
    mobile app (e.g. Flutter). Fields include id, title, content, author,
    image/video links, timestamps and simple interaction counts.
    """
    try:
        p = Post.objects.get(id=post_id, is_deleted=False)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    image_url = None
    if p.image:
        try:
            image_url = request.build_absolute_uri(p.image.url)
        except Exception:
            # Fallback to relative URL if building absolute fails
            image_url = getattr(p.image, "url", None)

    post_data = {
        "id": str(p.id),
        "title": p.title,
        "content": p.content,
        "author": getattr(p.user, "username", None),
        "image_url": image_url,
        "video_link": p.video_link,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "likes_count": p.likes_count,
        "dislikes_count": p.dislikes_count,
        "shares_count": p.shares_count,
        "is_deleted": p.is_deleted,
    }

    return JsonResponse(post_data)


def json_post_comments(request, post_id):
    """
    Returns comments for a specific post as JSON suitable for consumption by a
    mobile app (e.g. Flutter). Each comment includes id, content, author,
    timestamps.
    """
    try:
        p = Post.objects.get(id=post_id, is_deleted=False)
    except Post.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    comments_qs = p.comments.filter(is_deleted=False).order_by("created_at")
    comments_list = []
    for c in comments_qs:
        comments_list.append(
            {
                "id": str(c.id),
                "content": c.content,
                "author": getattr(c.user, "username", None),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
        )

    return JsonResponse(comments_list, safe=False)


@csrf_exempt
def create_post_flutter(request):
    """
    Endpoint to create a new post from a Flutter mobile app.
    Expects JSON payload with title, content, optional image and video_link.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method"}, status=401)

    try:
        data = json.loads(request.body)
        title = data.get("title")
        content = data.get("content")
        image_data = data.get("image")  # base64 string or data URI
        video_link = data.get("video_link", "")
        user_id = data.get("user_id")  # Assuming user_id is passed in payload

        user = User.objects.get(id=user_id)

        new_post = Post(user=user, title=title, content=content, video_link=video_link)

        # If an image was sent as base64 (possibly with a data-uri prefix), decode, validate and save
        if image_data:
            try:
                # Validation settings
                MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
                ALLOWED_MIME = {
                    "image/png",
                    "image/jpeg",
                    "image/jpg",
                    "image/webp",
                    "image/gif",
                }

                # If data URI, strip the prefix
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

                # Size check
                if len(decoded) > MAX_IMAGE_BYTES:
                    return JsonResponse(
                        {"error": "Image too large (max 5MB)"}, status=400
                    )

                # Determine mime if not provided — detect using magic bytes (avoid imghdr)
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


@csrf_exempt
def create_comment_flutter(request):
    """
    Endpoint to create a new comment from Flutter.
    Expects JSON payload: post_id, content, user_id, optional parent_id
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid HTTP method"}, status=401)

    try:
        data = json.loads(request.body)
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
                "message": "Comment created",
                "comment": {
                    "id": str(comment.id),
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
