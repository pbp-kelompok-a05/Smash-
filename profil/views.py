from django.shortcuts import render, redirect, get_object_or_404
from post.models import ForumPost, PostLike
from django.http import HttpResponseRedirect, JsonResponse
from account.models import Account
from profil.models import Profile
from profil.forms import ProfileForm


def show_views(request):
    account = get_object_or_404(Account, user=request.user)
    post_list = ForumPost.objects.all()
    like_list = PostLike.objects.all()
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
    post_list = ForumPost.objects.all()
    like_list = PostLike.objects.all()
    post_data = [
        {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "category": post.category,
            "image": post.image,
            "url_vid": post.video_url,
            "like": post.get_likes_count,
            "comment": post.get_comment_count,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "user_name": post.author.username,
            "author_id": post.author.id,
        }
        for post in post_list
    ]
    like_data = [
        {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "category": post.category,
            "image": post.image,
            "url_vid": post.video_url,
            "like": post.get_likes_count,
            "is_like": post.is_like,
            "comment": post.get_comment_count,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "user_name": post.author.username,
            "author_id": post.author.id,
        }
        for post in like_list
    ]
    data = {
        "post": post_data,
        "like": like_data,
    }
    return JsonResponse(data, safe=False)
