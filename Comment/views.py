from django.shortcuts import render, redirect, get_object_or_404
from Comment.models import Comment
from Comment.forms import CommentForm
from Post.models import ForumPost


def show_comments(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    comments = Comment.objects.filter(post=post).order_by("-created_at")

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user if request.user.is_authenticated else None
            comment.save()
            return redirect("show_comments", post_id=post.id)
    else:
        form = CommentForm()

    context = {
        "post": post,
        "comments": comments,
        "form": form,
    }
    return render(request, "comment_view.html", context)


def add_comment(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid() and request.method == "POST":
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect("show_comments", post_id=post.id)
    context = {"form": form, "post": post}
    return render(request, "comments/comment_form.html", context)
