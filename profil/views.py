from django.shortcuts import render, redirect, get_object_or_404
from post.models import Post
from django.http import HttpResponseRedirect, JsonResponse
from profil.models import Profile
from profil.forms import ProfileForm
from django.contrib.auth.decorators import login_required

@login_required(login_url='account:login_register')
def show_views(request):
    post_list = Post.objects.all()
    try:
        profile = Profile.objects.get(user=request.user)
        bio = profile.bio
    except Profile.DoesNotExist:
        bio = "Belum ada bio"
    context = {
        'post_list': post_list,
        'bio': bio,
    }
    return render(request, "profile_user.html", context)

# Create your views here.
def edit_or_create_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profil:show_views")

    context = {
        "form": form,
        "is_edit": not created,
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
