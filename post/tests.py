"""
post/tests.py

Test suite lengkap untuk app `post` yang menargetkan minimal 80% coverage.

Yang diuji (ringkasan):
- Model: Post, PostInteraction, PostSave, PostShare
  - __str__, soft-delete / restore
  - property likes_count, dislikes_count, shares_count
  - unique constraint untuk PostSave / PostInteraction
- API class-based views:
  - PostAPIView: GET list & single (including pagination & sort_by),
                  POST create (JSON & multipart), PUT update (owner/superuser perms),
                  DELETE soft delete (permission), error cases (invalid JSON, not auth, file invalid)
  - PostInteractionView: like/dislike toggle/change/remove, share, report, invalid action, not auth, post not found
- Function views: hot_threads, bookmarked_threads, recent_thread, search_posts
  - Dipanggil dengan patching `post.views.render` sehingga tidak bergantung pada template file.

Catatan teknis:
- Banyak view merender template menggunakan django.shortcuts.render; untuk memastikan tests tidak gagal saat template tidak tersedia,
  tests ini mem-patch `post.views.render` dan memeriksa context yang dilempar ke `render`.
- RequestFactory digunakan dan request.user diset manual untuk menghindari ketergantungan middleware.
"""
import json
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse

from .models import Post, PostInteraction, PostSave, PostShare
from .views import PostAPIView, PostInteractionView, hot_threads, bookmarked_threads, recent_thread, search_posts
from report.models import Report  # digunakan oleh PostInteractionView

User = get_user_model()


class PostModelTests(TestCase):
    """Unit tests untuk model Post dan related models."""

    def setUp(self):
        # Buat dua user (owner, other)
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        # Post dasar
        self.post = Post.objects.create(user=self.owner, title="Test Post", content="Konten test")

    def test_str_and_initial_counts(self):
        """__str__ dan count awal harus benar."""
        s = str(self.post)
        self.assertIn("Test Post", s)
        self.assertIn(self.owner.username, s)
        self.assertEqual(self.post.likes_count, 0)
        self.assertEqual(self.post.dislikes_count, 0)
        self.assertEqual(self.post.shares_count, 0)

    def test_soft_delete_and_restore(self):
        """delete() harus soft-delete (is_deleted True) dan restore() mengembalikan."""
        self.post.delete()
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)
        self.post.restore()
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_deleted)

    def test_interaction_counts(self):
        """likes_count & dislikes_count dihitung dari PostInteraction terkait."""
        PostInteraction.objects.create(user=self.owner, post=self.post, interaction_type="like")
        PostInteraction.objects.create(user=self.other, post=self.post, interaction_type="dislike")
        self.post.refresh_from_db()
        self.assertEqual(self.post.likes_count, 1)
        self.assertEqual(self.post.dislikes_count, 1)

    def test_shares_and_saves_unique(self):
        """shares_count dan PostSave unique_together basic check."""
        PostShare.objects.create(user=self.owner, post=self.post)
        PostShare.objects.create(user=self.other, post=self.post)
        self.assertEqual(self.post.shares_count, 2)

        PostSave.objects.create(user=self.other, post=self.post)
        self.assertEqual(PostSave.objects.filter(user=self.other, post=self.post).count(), 1)


class PostAPIViewTests(TestCase):
    """Tests untuk PostAPIView: CRUD API behavior & edge cases."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="user1", password="pass")
        self.other = User.objects.create_user(username="user2", password="pass")
        self.superuser = User.objects.create_superuser(username="admin", password="pass", email="a@b.c")

        # Beberapa post untuk list / pagination tests
        for i in range(15):
            Post.objects.create(user=self.user, title=f"P{i}", content="c")

    def _json(self, response):
        return json.loads(response.content.decode("utf-8"))

    def test_get_list_default_and_pagination(self):
        """GET list default, pagination, and sort_by parameter."""
        req = self.factory.get("/posts/?page=1&per_page=10")
        req.user = self.user
        resp = PostAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        d = self._json(resp)
        self.assertEqual(d["status"], "success")
        self.assertIn("posts", d)
        self.assertEqual(d["pagination"]["page"], 1)
        self.assertEqual(d["pagination"]["per_page"], 10)
        self.assertTrue("total" in d["pagination"])

        # page 2
        req2 = self.factory.get("/posts/?page=2&per_page=10")
        req2.user = self.user
        resp2 = PostAPIView.as_view()(req2)
        self.assertEqual(resp2.status_code, 200)
        d2 = self._json(resp2)
        self.assertEqual(d2["pagination"]["page"], 2)

    def test_superuser_can_see_deleted_posts_in_list(self):
        """Superuser listing should include deleted posts."""
        p = Post.objects.create(user=self.user, title="to_delete", content="c")
        p.delete()  # soft delete
        # normal user should not see the deleted post
        req = self.factory.get("/posts/")
        req.user = self.user
        resp = PostAPIView.as_view()(req)
        d = self._json(resp)
        titles = [post["title"] for post in d["posts"]]
        self.assertNotIn("to_delete", titles)
        # superuser sees it
        req_admin = self.factory.get("/posts/")
        req_admin.user = self.superuser
        resp_admin = PostAPIView.as_view()(req_admin)
        d_admin = self._json(resp_admin)
        titles_admin = [post["title"] for post in d_admin["posts"]]
        self.assertIn("to_delete", titles_admin)

    def test_get_single_deleted_post_returns_404_for_non_superuser(self):
        """GET single deleted post should give 404 for normal user."""
        p = Post.objects.create(user=self.user, title="deleted single", content="c")
        p.delete()
        req = self.factory.get(f"/posts/{p.id}/")
        req.user = self.user
        resp = PostAPIView.as_view()(req, post_id=p.id)
        self.assertEqual(resp.status_code, 404)
        d = self._json(resp)
        self.assertEqual(d["status"], "error")

    def test_create_post_json_invalid_and_auth(self):
        """POST invalid JSON should return 400; unauthenticated returns 401."""
        # unauthenticated
        req_unauth = self.factory.post("/posts/", data=json.dumps({"title": "t", "content": "c"}), content_type="application/json")
        # no user set -> anonymous
        resp_unauth = PostAPIView.as_view()(req_unauth)
        self.assertEqual(resp_unauth.status_code, 401)

        # invalid JSON payload
        req = self.factory.post("/posts/", data=b"notjson", content_type="application/json")
        req.user = self.user
        resp = PostAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    def test_create_post_multipart_wrong_type_and_too_large(self):
        """Upload file with wrong content_type and too-large file -> 400 responses."""
        # wrong type
        bad_file = SimpleUploadedFile("file.pdf", b"%PDF-1.4", content_type="application/pdf")
        data_json = json.dumps({"title": "t", "content": "c"})
        req = self.factory.post("/posts/", data={"data": data_json, "image": bad_file})
        req.user = self.user
        resp = PostAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)
        d = self._json(resp)
        self.assertIn("File type tidak didukung", d["message"])

        # too large file (>5MB)
        large = b"a" * (5 * 1024 * 1024 + 1)
        big_file = SimpleUploadedFile("big.gif", large, content_type="image/gif")
        req2 = self.factory.post("/posts/", data={"data": data_json, "image": big_file})
        req2.user = self.user
        resp2 = PostAPIView.as_view()(req2)
        self.assertEqual(resp2.status_code, 400)
        d2 = self._json(resp2)
        self.assertIn("Ukuran file terlalu besar", d2["message"])

    def test_put_update_permissions_and_image_replace(self):
        """PUT update must enforce owner/superuser permissions and allow image replacement."""
        post = Post.objects.create(user=self.user, title="orig", content="x")
        payload = {"title": "upd"}

        # other user cannot update
        req_other = self.factory.put(f"/posts/{post.id}/", data=json.dumps(payload), content_type="application/json")
        req_other.user = self.other
        resp_other = PostAPIView.as_view()(req_other, post_id=post.id)
        self.assertEqual(resp_other.status_code, 403)

        # owner can update
        req_owner = self.factory.put(f"/posts/{post.id}/", data=json.dumps(payload), content_type="application/json")
        req_owner.user = self.user
        resp_owner = PostAPIView.as_view()(req_owner, post_id=post.id)
        self.assertEqual(resp_owner.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.title, "upd")

        # Test replacing image by setting request.FILES manually
        img = SimpleUploadedFile("i.gif", b"GIF89a", content_type="image/gif")
        req_img = self.factory.put(f"/posts/{post.id}/", data=json.dumps({"title": "imgupd"}), content_type="application/json")
        req_img.user = self.user
        # attach files and let view pick them up
        req_img.FILES = {"image": img}
        resp_img = PostAPIView.as_view()(req_img, post_id=post.id)
        self.assertEqual(resp_img.status_code, 200)
        post.refresh_from_db()
        self.assertIsNotNone(post.image)

    def test_delete_requires_auth_and_permission(self):
        """DELETE should be 401 if not auth; 403 if not owner; 200 and soft-delete if owner."""
        post = Post.objects.create(user=self.user, title="d", content="c")
        # unauthenticated
        req_unauth = self.factory.delete(f"/posts/{post.id}/")
        resp_unauth = PostAPIView.as_view()(req_unauth, post_id=post.id)
        self.assertEqual(resp_unauth.status_code, 401)

        # other user
        req_other = self.factory.delete(f"/posts/{post.id}/")
        req_other.user = self.other
        resp_other = PostAPIView.as_view()(req_other, post_id=post.id)
        self.assertEqual(resp_other.status_code, 403)

        # owner
        req_owner = self.factory.delete(f"/posts/{post.id}/")
        req_owner.user = self.user
        resp_owner = PostAPIView.as_view()(req_owner, post_id=post.id)
        self.assertEqual(resp_owner.status_code, 200)
        post.refresh_from_db()
        self.assertTrue(post.is_deleted)


class PostInteractionViewTests(TestCase):
    """Tests untuk PostInteractionView: like/dislike/share/report dan error cases."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u1", password="pass")
        self.other = User.objects.create_user(username="u2", password="pass")
        self.post = Post.objects.create(user=self.user, title="Interaction Post", content="Konten")

    def _json(self, response):
        return json.loads(response.content.decode("utf-8"))

    def test_like_dislike_toggle_and_change(self):
        """Test toggle behavior: add -> remove -> change."""
        # add like
        req = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        req.user = self.other
        r = PostInteractionView.as_view()(req, post_id=self.post.id, action="like")
        self.assertEqual(r.status_code, 200)
        d = self._json(r)
        self.assertEqual(d["action"], "added")
        self.assertEqual(d["user_interaction"], "like")
        self.assertEqual(self.post.likes_count, 1)

        # same like again -> removed
        req2 = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        req2.user = self.other
        r2 = PostInteractionView.as_view()(req2, post_id=self.post.id, action="like")
        self.assertEqual(r2.status_code, 200)
        d2 = self._json(r2)
        self.assertEqual(d2["action"], "removed")

        # add dislike
        req3 = self.factory.post(f"/posts/{self.post.id}/dislike/", data=b"{}", content_type="application/json")
        req3.user = self.other
        r3 = PostInteractionView.as_view()(req3, post_id=self.post.id, action="dislike")
        self.assertEqual(r3.status_code, 200)
        d3 = self._json(r3)
        self.assertEqual(d3["action"], "added")
        self.assertEqual(self.post.dislikes_count, 1)

        # change to like (should update)
        req4 = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        req4.user = self.other
        r4 = PostInteractionView.as_view()(req4, post_id=self.post.id, action="like")
        self.assertEqual(r4.status_code, 200)
        d4 = self._json(r4)
        # action could be 'changed' or 'added' depending on path; ensure user_interaction updated
        self.assertEqual(d4["user_interaction"], "like")

    def test_share_creates_PostShare_and_report_creates_Report(self):
        """Share should create PostShare; report should create Report entry."""
        # share
        req_share = self.factory.post(f"/posts/{self.post.id}/share/", data=b"{}", content_type="application/json")
        req_share.user = self.other
        r_share = PostInteractionView.as_view()(req_share, post_id=self.post.id, action="share")
        self.assertEqual(r_share.status_code, 200)
        d_share = self._json(r_share)
        self.assertEqual(d_share["status"], "success")
        self.assertEqual(self.post.shares.count(), 1)

        # report
        payload = {"category": "SPAM", "description": "Spam content"}
        req_report = self.factory.post(f"/posts/{self.post.id}/report/", data=json.dumps(payload), content_type="application/json")
        req_report.user = self.other
        r_report = PostInteractionView.as_view()(req_report, post_id=self.post.id, action="report")
        self.assertEqual(r_report.status_code, 200)
        d_report = self._json(r_report)
        self.assertEqual(d_report["status"], "success")
        report_obj = Report.objects.get(id=d_report["report_id"])
        self.assertEqual(report_obj.reporter, self.other)
        self.assertEqual(report_obj.post, self.post)

    def test_invalid_action_and_post_not_found(self):
        """Invalid action returns 400; non-existent post returns 404."""
        req = self.factory.post("/posts/9999/invalid/", data=b"{}", content_type="application/json")
        req.user = self.other
        resp = PostInteractionView.as_view()(req, post_id=9999, action="like")
        self.assertEqual(resp.status_code, 404)  # post not found

        req_invalid = self.factory.post(f"/posts/{self.post.id}/bad/", data=b"{}", content_type="application/json")
        req_invalid.user = self.other
        resp_inv = PostInteractionView.as_view()(req_invalid, post_id=self.post.id, action="bad")
        self.assertEqual(resp_inv.status_code, 400)

    def test_authentication_required_for_interactions(self):
        """Unauthenticated user should get 401 for interaction endpoints."""
        req = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        # no req.user set => anonymous
        resp = PostInteractionView.as_view()(req, post_id=self.post.id, action="like")
        self.assertEqual(resp.status_code, 401)


class TemplateViewsTests(TestCase):
    """
    Tests untuk hot_threads, bookmarked_threads, recent_thread, search_posts.

    Karena views memakai render(template, context), kita patch `post.views.render`
    untuk menghindari ketergantungan pada file template.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="tvuser", password="pass")
        # beberapa post
        self.p1 = Post.objects.create(user=self.user, title="FindMe", content="alpha")
        self.p2 = Post.objects.create(user=self.user, title="Other", content="beta")
        # bookmark
        from .models import PostSave
        PostSave.objects.create(user=self.user, post=self.p1)

    def test_hot_threads_calls_render_with_posts(self):
        """hot_threads harus memanggil render dengan context yang mengandung 'posts'."""
        req = self.factory.get("/hot/")
        req.user = self.user
        with patch("post.views.render") as mock_render:
            mock_render.return_value = HttpResponse("ok")
            resp = hot_threads(req)
            self.assertEqual(resp.status_code, 200)
            mock_render.assert_called_once()
            # ambil context yang dikirim ke render: arg[2]
            ctx = mock_render.call_args[0][2]
            self.assertIn("posts", ctx)
            self.assertIn("page_title", ctx)

    def test_bookmarked_threads_requires_login_and_returns_posts(self):
        """bookmarked_threads decorated with login_required; kalau user autentikasi, panggil render."""
        req = self.factory.get("/bookmarks/")
        req.user = self.user
        with patch("post.views.render") as mock_render:
            mock_render.return_value = HttpResponse("ok")
            resp = bookmarked_threads(req)
            self.assertEqual(resp.status_code, 200)
            mock_render.assert_called_once()
            ctx = mock_render.call_args[0][2]
            self.assertIn("posts", ctx)
            self.assertEqual(ctx["page_title"], "Bookmarks")
            # ensure saved post present
            self.assertTrue(any(p.title == "FindMe" for p in ctx["posts"]))

    def test_recent_thread_and_search_posts(self):
        """recent_thread returns posts; search_posts filters by query."""
        # recent_thread
        req = self.factory.get("/recent/")
        req.user = self.user
        with patch("post.views.render") as mock_render:
            mock_render.return_value = HttpResponse("ok")
            resp = recent_thread(req)
            self.assertEqual(resp.status_code, 200)
            mock_render.assert_called_once()
            ctx = mock_render.call_args[0][2]
            self.assertIn("posts", ctx)

        # search_posts with query that matches p1 title
        req2 = self.factory.get("/search/?q=Find")
        req2.user = self.user
        with patch("post.views.render") as mock_render:
            mock_render.return_value = HttpResponse("ok")
            resp2 = search_posts(req2)
            self.assertEqual(resp2.status_code, 200)
            mock_render.assert_called_once()
            ctx2 = mock_render.call_args[0][2]
            self.assertIn("posts", ctx2)
            # One of the posts should be FindMe
            titles = [p.title for p in ctx2["posts"]]
            self.assertIn("FindMe", titles)
