import json
from django.shortcuts import render, redirect, get_object_or_404
from post.models import Post, PostSave, PostInteraction
from django.http import HttpResponseRedirect, JsonResponse
from profil.models import Profile
from profil.forms import ProfileForm
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.templatetags.static import static
from django.http import QueryDict

User = get_user_model()

@login_required(login_url='account:login_register')
def show_views(request, user_id=None):
    """
    Profile page that can show either the current user's profile or another user's profile.
    When viewing someone else, editing controls are hidden but their posts remain visible.
    """
    target_user = request.user if user_id is None else get_object_or_404(User, pk=user_id)
    profile, _ = Profile.objects.get_or_create(user=target_user)
    post_list = Post.objects.filter(user=target_user, is_deleted=False)
    bio = profile.bio if profile.bio else "Belum ada bio"
    is_owner = target_user == request.user

    context = {
        'post_list': post_list,
        'posts': post_list,
        'bio': bio,
        'profile': profile,
        'profile_user': target_user,
        'is_owner': is_owner,
    }
    return render(request, "profile_user.html", context)

# Create your views here.
@login_required(login_url='account:login_register')
def edit_or_create_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    existing_photo_name = profile.profile_photo.name if profile.profile_photo else None
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    show_messages = False

    if request.method == "POST":
        new_username = request.POST.get("username", "").strip()
        new_password = request.POST.get("password", "").strip()
        remove_photo_flag = str(request.POST.get("remove_photo", "")).lower() in ("true", "on", "1", "yes")
        uploaded_photo = request.FILES.get("profile_photo")

        if uploaded_photo:
            remove_photo_flag = False  # prioritize newly uploaded photo

        username_valid = True
        if new_username and new_username != request.user.username:
            if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                username_valid = False
                form.add_error(None, "Username sudah digunakan.")
                messages.error(request, "Username sudah digunakan, silakan pilih yang lain.")
            else:
                request.user.username = new_username

        password_changed = False
        if new_password:
            request.user.set_password(new_password)
            password_changed = True

        if form.is_valid() and username_valid:
            profile = form.save(commit=False)
            profile.user = request.user

            if uploaded_photo and existing_photo_name:
                profile.profile_photo.storage.delete(existing_photo_name)
            elif remove_photo_flag:
                if existing_photo_name:
                    profile.profile_photo.storage.delete(existing_photo_name)
                profile.profile_photo = None

            profile.save()
            request.user.save()

            if password_changed:
                update_session_auth_hash(request, request.user)

            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("profil:show_views")
        else:
            messages.error(request, "Gagal memperbarui profil. Mohon periksa kembali data Anda.")
        show_messages = True

    context = {
        "form": form,
        "is_edit": not created,
        "profile": profile,
        "show_messages": show_messages,
    }
    return render(request, "edit_profile.html", context)


@login_required(login_url='account:login_register')
@csrf_exempt
@require_POST
def change_password_api(request):
    """
    Change password endpoint used by the profile page.
    Expects: old_password, new_password, confirm_password (JSON or form-encoded).
    """
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"status": False, "message": "Payload tidak valid."}, status=400)
    else:
        data = request.POST

    old_password = (data.get("old_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()
    confirm_password = (data.get("confirm_password") or "").strip()

    if not old_password or not new_password or not confirm_password:
        return JsonResponse(
            {"status": False, "message": "Old password, new password, dan konfirmasi wajib diisi."},
            status=400,
        )

    if not request.user.check_password(old_password):
        return JsonResponse({"status": False, "message": "Old password tidak sesuai."}, status=400)

    if new_password != confirm_password:
        return JsonResponse({"status": False, "message": "Konfirmasi password tidak cocok."}, status=400)

    if new_password == old_password:
        return JsonResponse({"status": False, "message": "Password baru tidak boleh sama dengan yang lama."}, status=400)

    try:
        validate_password(new_password, user=request.user)
    except ValidationError as exc:
        return JsonResponse({"status": False, "message": "; ".join(exc)}, status=400)

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)

    return JsonResponse({"status": True, "message": "Password berhasil diperbarui."}, status=200)


def show_json(request):
    post_list = Post.objects.all()
    data = [
        {
            "title": post.title,
            "content": post.content,
            "image": post.image.url if post.image else None,
            "url_vid": post.video_link,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "user_name": post.user.username,
            "author_id": post.user.id,
        }
        for post in post_list
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def profile_api(request, user_id=None):
    """
    API endpoint for fetching and updating user profiles.
    - GET /profil/api/profile/ (requires login) returns the authenticated user's profile.
    - GET /profil/api/profile/<user_id>/ returns a user's profile by id.
    - POST/PATCH /profil/api/profile/ (requires login) updates the authenticated user's profile.
      Accepts JSON or multipart (for profile_photo). Use `remove_photo=true` to delete the
      current profile picture and revert to the default avatar.
    """

    def serialize(profile_obj):
        if profile_obj.profile_photo:
            photo_url = profile_obj.profile_photo.url
        else:
            photo_url = static("images/user-profile.png")

        photo_url = request.build_absolute_uri(photo_url)
        return {
            "id": profile_obj.user.id,
            "username": profile_obj.user.username,
            "bio": profile_obj.bio,
            "profile_photo": photo_url,
            "date_joined": profile_obj.user.date_joined.isoformat()
            if profile_obj.user.date_joined
            else None,
        }

    if request.method == "GET":
        if user_id is None:
            if not request.user.is_authenticated:
                return JsonResponse({"status": False, "message": "Authentication required."}, status=401)
            target_user = request.user
        else:
            target_user = get_object_or_404(User, pk=user_id)

        profile, _ = Profile.objects.get_or_create(user=target_user)
        return JsonResponse({"status": True, "data": serialize(profile)}, status=200)

    if request.method in ("POST", "PATCH", "PUT"):
        if not request.user.is_authenticated:
            return JsonResponse({"status": False, "message": "Authentication required."}, status=401)

        if user_id is not None and request.user.id != user_id:
            return JsonResponse({"status": False, "message": "You can only update your own profile."}, status=403)

        profile, _ = Profile.objects.get_or_create(user=request.user)

        if request.content_type and "application/json" in request.content_type:
            try:
                data = json.loads(request.body or "{}")
            except json.JSONDecodeError:
                return JsonResponse({"status": False, "message": "Invalid JSON payload."}, status=400)
        elif request.method in ("PATCH", "PUT") and request.content_type:
            data = QueryDict(request.body)
        else:
            data = request.POST

        new_username = data.get("username")
        if new_username:
            normalized_username = new_username.lower()
            if User.objects.filter(username__iexact=normalized_username).exclude(pk=request.user.pk).exists():
                return JsonResponse({"status": False, "message": "Username already exists."}, status=400)
            request.user.username = normalized_username

        if "bio" in data:
            profile.bio = data.get("bio") or ""

        remove_photo = str(data.get("remove_photo", "")).lower() == "true"

        if request.FILES.get("profile_photo"):
            if profile.profile_photo:
                profile.profile_photo.delete(save=False)
            profile.profile_photo = request.FILES["profile_photo"]
            remove_photo = False  # prioritize the newly uploaded photo
        elif remove_photo:
            if profile.profile_photo:
                profile.profile_photo.delete(save=False)
            profile.profile_photo = None

        request.user.save()
        profile.save()

        return JsonResponse({"status": True, "message": "Profile updated.", "data": serialize(profile)}, status=200)

    return JsonResponse({"status": False, "message": "Method not allowed."}, status=405)


@login_required(login_url='account:login_register')
def profile_posts_api(request):
    """
    JSON endpoint to fetch profile posts filtered by:
    - filter=my (default): posts by the current user
    - filter=bookmarked: posts the user bookmarked
    - filter=liked: posts the user liked
    - user_id=<id>: view posts for a specific user (filters ignored unless it's your own profile)
    Supports simple pagination with ?page=&per_page=
    """
    if request.method != "GET":
        return JsonResponse({"status": False, "message": "Method not allowed."}, status=405)

    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = max(min(int(request.GET.get("per_page", 10)), 50), 1)
    except (TypeError, ValueError):
        per_page = 10

    filter_param = request.GET.get("filter", "my").lower()
    target_user_id = request.GET.get("user_id")

    target_user = request.user
    if target_user_id:
        try:
            target_user = User.objects.get(pk=target_user_id)
        except User.DoesNotExist:
            return JsonResponse({"status": False, "message": "User not found."}, status=404)

    is_owner = target_user == request.user

    base_qs = Post.objects.filter(is_deleted=False).select_related("user")
    if not is_owner:
        base_qs = base_qs.filter(user=target_user)

    user_interactions = dict(
        PostInteraction.objects.filter(user=request.user).values_list("post_id", "interaction_type")
    )
    saved_post_ids = set(
        PostSave.objects.filter(user=request.user).values_list("post_id", flat=True)
    )

    if is_owner:
        if filter_param == "bookmarked":
            posts_qs = base_qs.filter(id__in=saved_post_ids)
        elif filter_param == "liked":
            liked_ids = [pid for pid, action in user_interactions.items() if action == "like"]
            posts_qs = base_qs.filter(id__in=liked_ids)
        else:  # default "my"
            posts_qs = base_qs.filter(user=request.user)
    else:
        posts_qs = base_qs.filter(user=target_user)

    total = posts_qs.count()
    start = (page - 1) * per_page
    end = start + per_page
    posts = posts_qs.order_by("-created_at")[start:end]

    profile_cache = {}

    def get_profile_photo_url(user_obj):
        if user_obj.id in profile_cache:
            return profile_cache[user_obj.id]
        profile_obj = Profile.objects.filter(user=user_obj).first()
        url = profile_obj.profile_photo.url if profile_obj and profile_obj.profile_photo else None
        profile_cache[user_obj.id] = url
        return url

    serialized = []
    for post in posts:
        serialized.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "image": post.image.url if post.image else None,
                "video_link": post.video_link,
                "user": post.user.username,
                "user_id": post.user.id,
                "created_at": post.created_at.isoformat(),
                "comment_count": post.comments.filter(is_deleted=False).count(),
                "likes_count": post.likes_count,
                "dislikes_count": post.dislikes_count,
                "shares_count": post.shares_count,
                "profile_photo": get_profile_photo_url(post.user),
                "user_interaction": user_interactions.get(post.id),
                "is_saved": post.id in saved_post_ids,
                "can_edit": post.user_id == request.user.id or request.user.is_superuser,
            }
        )

    return JsonResponse(
        {
            "status": "success",
            "data": serialized,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "has_next": end < total,
            },
        }
    )
