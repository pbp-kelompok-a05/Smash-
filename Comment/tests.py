from django.test import TestCase
from django.contrib.auth.models import User
import uuid
import time

from .models import Comment
from Post.models import ForumPost
from django.test import RequestFactory
from django.http import HttpResponse
from unittest.mock import patch
from Comment.views import show_comments, add_comment
from Comment.forms import CommentForm


class CommentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pw")
        self.post = ForumPost.objects.create(
            title="Test Post",
            content="Post content",
            author=self.user,
            category="discussion",
        )

    def test_create_comment_fields(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="hello")
        self.assertIsInstance(c.id, uuid.UUID)
        self.assertEqual(c.content, "hello")
        self.assertEqual(c.post, self.post)
        self.assertEqual(c.author, self.user)
        self.assertIsNotNone(c.created_at)
        self.assertIsNotNone(c.updated_at)

    def test_related_name_and_count(self):
        Comment.objects.create(post=self.post, author=self.user, content="a")
        Comment.objects.create(post=self.post, author=self.user, content="b")
        self.assertEqual(self.post.comments.count(), 2)
        contents = list(self.post.comments.values_list("content", flat=True))
        self.assertIn("a", contents)
        self.assertIn("b", contents)

    def test_str(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="xyz")
        self.assertIn("Comment", str(c))
        self.assertIn(str(self.post), str(c))

    def test_author_nullable(self):
        c = Comment.objects.create(post=self.post, author=None, content="no author")
        self.assertIsNone(c.author)
        self.assertIsInstance(str(c), str)

    def test_updated_at_changes_but_created_at_stays(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="first")
        old_created = c.created_at
        old_updated = c.updated_at
        time.sleep(0.1)
        c.content = "second"
        c.save()
        c.refresh_from_db()
        self.assertEqual(c.created_at, old_created)
        self.assertGreater(c.updated_at, old_updated)

    def test_post_delete_cascades(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="x")
        self.post.delete()
        self.assertFalse(Comment.objects.filter(id=c.id).exists())

    def test_like_increments(self):
        self.assertEqual(self.post.likes, 0)
        self.post.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)
        self.post.like()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 2)

    def test_dislike_increments(self):
        self.assertEqual(self.post.dislikes, 0)
        self.post.dislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 1)
        self.post.dislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 2)

    def test_unlike_decrements_and_not_below_zero(self):
        self.assertEqual(self.post.likes, 0)
        self.post.unlike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 0)

        self.post.likes = 2
        self.post.save()
        self.post.unlike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 1)
        self.post.unlike()
        self.post.unlike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes, 0)

    def test_undislike_decrements_and_not_below_zero(self):
        self.assertEqual(self.post.dislikes, 0)
        self.post.undislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 0)

        self.post.dislikes = 2
        self.post.save()
        self.post.undislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 1)
        self.post.undislike()
        self.post.undislike()
        self.post.refresh_from_db()
        self.assertEqual(self.post.dislikes, 0)

    def test_comment_like_dislike_increment(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="c1")
        self.assertEqual(c.likes, 0)
        self.assertEqual(c.dislikes, 0)

        c.like()
        c.refresh_from_db()
        self.assertEqual(c.likes, 1)
        c.like()
        c.refresh_from_db()
        self.assertEqual(c.likes, 2)

        c.dislike()
        c.refresh_from_db()
        self.assertEqual(c.dislikes, 1)
        c.dislike()
        c.refresh_from_db()
        self.assertEqual(c.dislikes, 2)

    def test_comment_unlike_undislike_not_below_zero(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="c2")
        c.unlike()
        c.undislike()
        c.refresh_from_db()
        self.assertEqual(c.likes, 0)
        self.assertEqual(c.dislikes, 0)

        c.likes = 2
        c.dislikes = 2
        c.save()
        c.unlike()
        c.undislike()
        c.refresh_from_db()
        self.assertEqual(c.likes, 1)
        self.assertEqual(c.dislikes, 1)

        c.unlike()
        c.unlike()
        c.undislike()
        c.undislike()
        c.refresh_from_db()
        self.assertEqual(c.likes, 0)
        self.assertEqual(c.dislikes, 0)

    def test_comment_str_exact_and_none_author(self):
        c = Comment.objects.create(post=self.post, author=self.user, content="c3")
        expected = f"Comment by {self.user} on {self.post.title}"
        self.assertEqual(str(c), expected)

        c2 = Comment.objects.create(post=self.post, author=None, content="c4")
        s = str(c2)
        self.assertTrue(s.startswith("Comment by"))
        self.assertIn(self.post.title, s)

    def test_comment_form_validates_and_saves(self):
        form = CommentForm(data={"content": "form comment"})
        self.assertTrue(form.is_valid())
        comment = form.save(commit=False)
        comment.post = self.post
        comment.author = self.user
        comment.save()
        self.assertTrue(
            Comment.objects.filter(post=self.post, content="form comment").exists()
        )

    def test_show_comments_view_calls_render_with_comments(self):
        rf = RequestFactory()
        req = rf.get(f"/posts/{self.post.id}/comments/")
        Comment.objects.create(post=self.post, author=self.user, content="a")
        Comment.objects.create(post=self.post, author=self.user, content="b")
        with patch("Comment.views.render") as mock_render:
            mock_render.return_value = HttpResponse("ok")
            resp = show_comments(req, post_id=self.post.id)
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            self.assertEqual(args[0], req)
            self.assertEqual(args[1], "comments/comment_list.html")
            context = args[2]
            self.assertIn("comments", context)
            contents = list(context["comments"].values_list("content", flat=True))
            self.assertIn("b", contents)

    def test_add_comment_get_renders_form(self):
        rf = RequestFactory()
        req = rf.get(f"/posts/{self.post.id}/comments/add/")
        req.user = self.user
        with patch("Comment.views.render") as mock_render:
            mock_render.return_value = HttpResponse("ok")
            resp = add_comment(req, post_id=self.post.id)
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            self.assertEqual(args[1], "comments/comment_form.html")
            context = args[2]
            self.assertIn("form", context)
            self.assertIn("post", context)
            self.assertEqual(context["post"], self.post)

    def test_add_comment_post_creates_comment_and_redirects(self):
        rf = RequestFactory()
        req = rf.post(
            f"/posts/{self.post.id}/comments/add/", {"content": "new comment"}
        )
        req.user = self.user
        with patch("Comment.views.redirect") as mock_redirect:
            mock_redirect.return_value = HttpResponse("redirected")
            resp = add_comment(req, post_id=self.post.id)
            mock_redirect.assert_called_once_with("show_comments", post_id=self.post.id)
            c = Comment.objects.filter(post=self.post, content="new comment").first()
            self.assertIsNotNone(c)
            self.assertEqual(c.author, self.user)
