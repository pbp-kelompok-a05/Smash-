from django.shortcuts import render, redirect, get_object_or_404
from post.models import Post
from django.http import HttpResponseRedirect, JsonResponse
from profil.models import Profile
from profil.forms import ProfileForm
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required

User = get_user_model()

@login_required(login_url='account:login_register')
def show_views(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    post_list = Post.objects.filter(user=request.user, is_deleted=False)
    bio = profile.bio if profile.bio else "Belum ada bio"
    context = {
        'post_list': post_list,
        'posts': post_list,
        'bio': bio,
        'profile': profile,
    }
    return render(request, "profile_user.html", context)

# Create your views here.
@login_required(login_url='account:login_register')
def edit_or_create_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    show_messages = False

    if request.method == "POST":
        new_username = request.POST.get("username", "").strip()
        new_password = request.POST.get("password", "").strip()

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
