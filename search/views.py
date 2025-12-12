import json
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q, Count
from post.models import Post, PostInteraction, PostSave
from profil.models import Profile


def _profile_photo(user, cache):
    if user.id in cache:
        return cache[user.id]
    profile = Profile.objects.filter(user=user).first()
    cache[user.id] = profile.profile_photo.url if profile and profile.profile_photo else None
    return cache[user.id]


def search_posts(request):
    query = (request.GET.get("q") or "").strip()
    posts_qs = Post.objects.none()

    if query:
        posts_qs = (
            Post.objects.filter(is_deleted=False)
            .select_related("user")
            .annotate(comment_count=Count("comments", filter=Q(comments__is_deleted=False)))
            .filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(user__username__icontains=query)
            )
            .order_by("-created_at")
        )

    user_interactions = {}
    saved_post_ids = set()
    if request.user.is_authenticated and posts_qs.exists():
        user_interactions = dict(
            PostInteraction.objects.filter(
                user=request.user, post__in=posts_qs
            ).values_list("post_id", "interaction_type")
        )
        saved_post_ids = set(
            PostSave.objects.filter(user=request.user, post__in=posts_qs).values_list(
                "post_id", flat=True
            )
        )

    posts = []
    for post in posts_qs:
        post.user_interaction = user_interactions.get(post.id)
        post.is_saved = post.id in saved_post_ids
        posts.append(post)

    return render(request, "search_results.html", {"posts": posts, "query": query})


def search_posts_api(request):
    """
    API: search posts by title/content/username.
    Returns JSON list with core fields and profile photo.
    """
    query = (request.GET.get("q") or "").strip()
    posts = []
    if query:
        posts_qs = (
            Post.objects.filter(is_deleted=False)
            .select_related("user")
            .filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(user__username__icontains=query)
            )
            .order_by("-created_at")[:50]
        )

        profile_cache = {}

        for post in posts_qs:
            posts.append(
                {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "user": post.user.username,
                    "user_id": post.user.id,
                    "created_at": post.created_at.isoformat() if post.created_at else None,
                    "likes_count": post.likes_count,
                    "dislikes_count": post.dislikes_count,
                    "comment_count": post.comments.filter(is_deleted=False).count(),
                    "image": post.image.url if post.image else None,
                    "video_link": post.video_link,
                    "profile_photo": _profile_photo(post.user, profile_cache),
                }
            )

    return JsonResponse({"status": "success", "posts": posts})
