from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.templatetags.static import static

from comment.models import Comment, CommentInteraction
from post.models import PostInteraction
from profil.models import Profile


def _safe_iter(qs):
    iterator = qs.iterator()
    while True:
        try:
            yield next(iterator)
        except StopIteration:
            break
        except (ValueError, TypeError, AttributeError):
            continue


def _actor_photo(user, cache, default_photo):
    if not user:
        return default_photo
    if user.id in cache:
        return cache[user.id]
    profile = Profile.objects.filter(user=user).first()
    url = profile.profile_photo.url if profile and profile.profile_photo else default_photo
    cache[user.id] = url
    return url


def build_notifications(user):
    default_photo = static("images/user-profile.png")
    cache = {}

    post_interactions = (
        PostInteraction.objects.filter(post__user=user, post__is_deleted=False)
        .select_related("user", "post")
        .order_by("-id")[:50]
    )

    recent_comments = (
        Comment.objects.filter(post__user=user, post__is_deleted=False, is_deleted=False)
        .exclude(user=user)
        .select_related("user", "post")
        .order_by("-created_at")[:50]
    )

    replies_to_user_comments = (
        Comment.objects.filter(parent__user=user, is_deleted=False, post__is_deleted=False)
        .exclude(user=user)
        .select_related("user", "post", "parent")
        .order_by("-created_at")[:50]
    )

    comment_interactions = (
        CommentInteraction.objects.filter(comment__user=user)
        .exclude(user=user)
        .select_related("user", "comment", "comment__post")
        .order_by("-created_at")[:50]
    )

    notifications = []

    for pi in _safe_iter(post_interactions):
        if pi.user_id == user.id or (pi.post and getattr(pi.post, "is_deleted", False)):
            continue
        notifications.append(
            {
                "type": f"{pi.interaction_type}_post",
                "actor": pi.user.username,
                "actor_profile_photo": _actor_photo(pi.user, cache, default_photo),
                "actor_id": pi.user.id,
                "post_title": pi.post.title,
                "post_id": pi.post.id,
                "message": f"@{pi.user.username} {pi.interaction_type}d your post",
                "message_text": f"{pi.interaction_type}d your post",
                "timestamp": getattr(pi, "created_at", None),
            }
        )

    for c in _safe_iter(recent_comments):
        if not c.post or getattr(c.post, "is_deleted", False):
            continue
        note_type = "reply" if c.parent_id else "comment"
        notifications.append(
            {
                "type": note_type,
                "actor": c.user.username,
                "actor_profile_photo": _actor_photo(c.user, cache, default_photo),
                "actor_id": c.user.id,
                "post_title": c.post.title,
                "post_id": c.post.id,
                "content": c.content,
                "message": f"@{c.user.username} {'replied to your comment' if c.parent_id else 'commented on your post'}",
                "message_text": "replied to your comment" if c.parent_id else "commented on your post",
                "timestamp": getattr(c, "created_at", None),
            }
        )

    for rc in _safe_iter(replies_to_user_comments):
        if not rc.post or getattr(rc.post, "is_deleted", False):
            continue
        notifications.append(
            {
                "type": "reply_to_comment",
                "actor": rc.user.username,
                "actor_profile_photo": _actor_photo(rc.user, cache, default_photo),
                "actor_id": rc.user.id,
                "post_title": rc.post.title,
                "post_id": rc.post.id,
                "content": rc.content,
                "message": f"@{rc.user.username} replied to your comment",
                "message_text": "replied to your comment",
                "timestamp": getattr(rc, "created_at", None),
            }
        )

    for ci in _safe_iter(comment_interactions):
        if not ci.comment or ci.comment.is_deleted:
            continue
        if ci.comment.post and getattr(ci.comment.post, "is_deleted", False):
            continue
        verb = "liked" if ci.interaction_type == "like" else "disliked"
        notifications.append(
            {
                "type": f"{ci.interaction_type}_comment",
                "actor": ci.user.username,
                "actor_profile_photo": _actor_photo(ci.user, cache, default_photo),
                "actor_id": ci.user.id,
                "post_title": ci.comment.post.title,
                "post_id": ci.comment.post.id,
                "content": ci.comment.content,
                "message": f"@{ci.user.username} {verb} your comment",
                "message_text": f"{verb} your comment",
                "timestamp": getattr(ci, "created_at", None),
            }
        )

    notifications.sort(key=lambda n: n.get("timestamp") or 0, reverse=True)
    return notifications


def serialize_for_api(notifications):
    serialized = []
    for n in notifications:
        ts = n.get("timestamp")
        serialized.append({**n, "timestamp": ts.isoformat() if ts else None})
    return serialized


@login_required
def notifications_view(request):
    notifications = build_notifications(request.user)
    return render(request, "notifications.html", {"notifications": notifications})


@login_required
def notifications_api(request):
    notifications = serialize_for_api(build_notifications(request.user))
    for n in notifications:
        actor_id = n.get("actor_id")
        n["actor_profile_url"] = reverse("profil:user_profile", args=[actor_id]) if actor_id else None
    return JsonResponse({"status": "success", "notifications": notifications})
