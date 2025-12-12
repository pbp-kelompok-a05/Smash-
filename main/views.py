# main/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from post.models import Post, User
from ads.models import Advertisement
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
        image = data.get("image")  # Assuming image is handled separately
        video_link = data.get("video_link", "")
        user_id = data.get("user_id")  # Assuming user_id is passed in payload

        user = User.objects.get(id=user_id)

        new_post = Post(
            user=user,
            title=title,
            content=content,
            image=image,
            video_link=video_link,
        )
        new_post.save()

        return JsonResponse(
            {
                "message": "Post created successfully",
                "post_id": str(new_post.id),
            },
            status=201,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
