from django.shortcuts import render, redirect, get_object_or_404
from post.models import Post
from django.http import HttpResponseRedirect, JsonResponse
from profil.models import Profile
from profil.forms import ProfileForm


def show_views(request):
    post_list = Post.objects.all()
    return render(request, "main.html")


# Create your views here.
def create_profil(request):
    profil = get_object_or_404(Profile, user=request.user)
    form = ProfileForm(request.POST or None, instance=profil)
    if form.is_valid() and request.method == "POST":
        profil_entry = form.save(commit=False)
        profil_entry.user = request.user
        profil_entry.save()
        return redirect("profil:show_views")
    context = {"form": form}
    return render(request, "edit_profile.html", context)


def show_json(request):
    post_list = Post.objects.all()
    data = [
        {
            "author": post.user,
            "title": post.title,
            "content": post.content,
            "image": post.image,
            "url_vid": post.video_link,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "user_name": post.user.username,
            "author_id": post.user.id,
        }
        for post in post_list
    ]
    return JsonResponse(data, safe=False)
