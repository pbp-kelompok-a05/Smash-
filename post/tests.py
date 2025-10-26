"""
post/tests.py

Test suite untuk app `post`.

Yang diuji:
- Behavior model Post, PostInteraction, PostSave, PostShare:
  - __str__, soft delete (delete/restore), properti likes_count/dislikes_count/shares_count
- Endpoint/CBV API (dipanggil langsung lewat RequestFactory):
  - GET list & single post (kondisi normal)
  - POST create post (JSON & multipart with image)
  - PUT update post (permission: owner / superuser)
  - DELETE soft-delete (permission)
- Interaksi: like / dislike toggle, change interaction, share, report

Catatan:
- Test ini menggunakan RequestFactory dan memanggil .as_view() pada class-based views
  sehingga tidak bergantung pada urlconf proyek.
- CSRF tidak menjadi masalah karena dispatch di-`csrf_exempt` di views asli.
"""
import json
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .models import Post, PostInteraction, PostSave, PostShare
from .views import PostAPIView, PostInteractionView
# Jika Report ada di report.models (views import menggunakannya), ikut import untuk validasi report dibuat
from report.models import Report

User = get_user_model()


class PostModelTests(TestCase):
    """Test unit untuk model Post dan related models (interactions, saves, shares)."""

    def setUp(self):
        # Buat 2 user: owner dan other
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")

        # Buat sebuah post
        self.post = Post.objects.create(
            user=self.owner,
            title="Test Post",
            content="Konten test"
        )

    def test_str_and_basic_properties(self):
        """__str__ harus mereturn 'title oleh username' dan counts awal 0."""
        self.assertIn("Test Post", str(self.post))
        self.assertIn(self.owner.username, str(self.post))
        self.assertEqual(self.post.likes_count, 0)
        self.assertEqual(self.post.dislikes_count, 0)
        self.assertEqual(self.post.shares_count, 0)

    def test_soft_delete_and_restore(self):
        """Memanggil delete() -> is_deleted True; restore() -> kembali False."""
        self.post.delete()
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)

        self.post.restore()
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_deleted)

    def test_likes_dislikes_counts(self):
        """
        Buat beberapa interaksi seperti like & dislike -> pastikan properti menghitung dengan benar.
        - owner -> like
        - other -> dislike
        """
        PostInteraction.objects.create(user=self.owner, post=self.post, interaction_type="like")
        PostInteraction.objects.create(user=self.other, post=self.post, interaction_type="dislike")

        self.post.refresh_from_db()
        self.assertEqual(self.post.likes_count, 1)
        self.assertEqual(self.post.dislikes_count, 1)

    def test_shares_and_saves(self):
        """Test shares_count dan PostSave unique constraint behavior sederhana."""
        # share oleh owner dan other
        PostShare.objects.create(user=self.owner, post=self.post)
        PostShare.objects.create(user=self.other, post=self.post)
        self.assertEqual(self.post.shares_count, 2)

        # save/ bookmark
        s = PostSave.objects.create(user=self.other, post=self.post)
        self.assertIn(s, PostSave.objects.filter(user=self.other))
        # mencoba membuat save yang sama lagi akan menimbulkan IntegrityError di DB (unique_together)
        # namun kita cukup cek bahwa satu entri ada
        self.assertEqual(PostSave.objects.filter(user=self.other, post=self.post).count(), 1)


class PostAPIViewTests(TestCase):
    """Test untuk PostAPIView (CRUD) dengan RequestFactory."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="user1", password="pass")
        self.other = User.objects.create_user(username="user2", password="pass")
        self.superuser = User.objects.create_superuser(username="admin", password="pass", email="a@b.c")

        # Post sample
        self.post = Post.objects.create(user=self.user, title="API Post", content="Konten API")

    def _get_json_response(self, response):
        """Helper: parse JsonResponse content menjadi dict."""
        return json.loads(response.content.decode("utf-8"))

    def test_get_post_list_and_single(self):
        """GET list (no auth) dan GET single (no auth) harus sukses."""
        # GET list
        req_list = self.factory.get("/posts/?page=1&per_page=10")
        # Anonymous user; RequestFactory default user is AnonymousUser, yang punya attribute is_authenticated False
        req_list.user = self.user  # juga bisa test sebagai authenticated
        resp_list = PostAPIView.as_view()(req_list)
        self.assertEqual(resp_list.status_code, 200)
        data = self._get_json_response(resp_list)
        self.assertEqual(data["status"], "success")
        self.assertIn("posts", data)
        self.assertGreaterEqual(data["pagination"]["total"], 1)

        # GET single
        req_single = self.factory.get(f"/posts/{self.post.id}/")
        req_single.user = self.user
        resp_single = PostAPIView.as_view()(req_single, post_id=self.post.id)
        self.assertEqual(resp_single.status_code, 200)
        d_single = self._get_json_response(resp_single)
        self.assertEqual(d_single["status"], "success")
        self.assertEqual(d_single["post"]["id"], self.post.id)

    def test_create_post_json(self):
        """POST create post dengan JSON sebagai user ter-autentikasi -> status 201."""
        payload = {"title": "New JSON Post", "content": "Isi dari JSON"}
        req = self.factory.post("/posts/", data=json.dumps(payload), content_type="application/json")
        req.user = self.user
        resp = PostAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 201)
        d = self._get_json_response(resp)
        self.assertEqual(d["status"], "success")
        self.assertIn("post_id", d)

        # Pastikan post benar-benar dibuat di DB
        created = Post.objects.get(id=d["post_id"])
        self.assertEqual(created.title, payload["title"])
        self.assertEqual(created.user, self.user)

    def test_create_post_multipart_with_image(self):
        """POST create menggunakan multipart/form-data dengan field 'data' berisi JSON dan file gambar."""
        # Siapkan file gambar sederhana (png)
        image_content = b"\x47\x49\x46\x38\x39\x61"  # GIF header kecil; views mengizinkan gif/png/jpg
        uploaded = SimpleUploadedFile("test.gif", image_content, content_type="image/gif")

        data_json = json.dumps({"title": "Post with image", "content": "Has image"})
        # RequestFactory akan mendeteksi multipart bila ada uploaded file di data
        req = self.factory.post("/posts/", data={"data": data_json, "image": uploaded})
        req.user = self.user
        # Tidak set content_type => factory akan membuat multipart untuk file
        resp = PostAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 201)
        d = self._get_json_response(resp)
        self.assertEqual(d["status"], "success")
        self.assertIsNotNone(d["post"]["image"])

    def test_update_post_permissions_and_put(self):
        """PUT update: hanya owner atau superuser boleh. Cek behavior update dan permission denied."""
        # Update by other user -> should be 403
        payload = {"title": "Hacked Title"}
        req_other = self.factory.put(f"/posts/{self.post.id}/", data=json.dumps(payload), content_type="application/json")
        req_other.user = self.other
        resp_other = PostAPIView.as_view()(req_other, post_id=self.post.id)
        self.assertEqual(resp_other.status_code, 403)

        # Update by owner -> success
        req_owner = self.factory.put(f"/posts/{self.post.id}/", data=json.dumps(payload), content_type="application/json")
        req_owner.user = self.user
        resp_owner = PostAPIView.as_view()(req_owner, post_id=self.post.id)
        self.assertEqual(resp_owner.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Hacked Title")

        # Update by superuser -> success
        payload2 = {"title": "Admin Updated"}
        req_admin = self.factory.put(f"/posts/{self.post.id}/", data=json.dumps(payload2), content_type="application/json")
        req_admin.user = self.superuser
        resp_admin = PostAPIView.as_view()(req_admin, post_id=self.post.id)
        self.assertEqual(resp_admin.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Admin Updated")

    def test_delete_post_soft_and_permissions(self):
        """DELETE soft delete: hanya owner atau superuser -> is_deleted True."""
        # other user cannot delete
        req_other = self.factory.delete(f"/posts/{self.post.id}/")
        req_other.user = self.other
        resp_other = PostAPIView.as_view()(req_other, post_id=self.post.id)
        self.assertEqual(resp_other.status_code, 403)

        # owner can delete
        req_owner = self.factory.delete(f"/posts/{self.post.id}/")
        req_owner.user = self.user
        resp_owner = PostAPIView.as_view()(req_owner, post_id=self.post.id)
        self.assertEqual(resp_owner.status_code, 200)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_deleted)


class PostInteractionViewTests(TestCase):
    """Test untuk PostInteractionView (like/dislike/report/share)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u1", password="pass")
        self.other = User.objects.create_user(username="u2", password="pass")
        self.post = Post.objects.create(user=self.user, title="Interaction Post", content="Konten")

    def _get_json_response(self, response):
        return json.loads(response.content.decode("utf-8"))

    def test_like_toggle_and_change(self):
        """Test toggle behaviour:
        - first like -> create interaction (added)
        - second like -> remove interaction (removed)
        - then dislike -> change interaction (changed/added)
        """
        # First like
        req_like = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        req_like.user = self.other
        resp1 = PostInteractionView.as_view()(req_like, post_id=self.post.id, action="like")
        self.assertEqual(resp1.status_code, 200)
        d1 = self._get_json_response(resp1)
        self.assertEqual(d1["action"], "added")
        self.assertEqual(d1["user_interaction"], "like")
        self.assertEqual(self.post.likes_count, 1)

        # Second like (same user) -> should remove
        req_like2 = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        req_like2.user = self.other
        resp2 = PostInteractionView.as_view()(req_like2, post_id=self.post.id, action="like")
        self.assertEqual(resp2.status_code, 200)
        d2 = self._get_json_response(resp2)
        self.assertEqual(d2["action"], "removed")
        self.assertIsNone(d2["user_interaction"])
        self.assertEqual(self.post.likes_count, 0)

        # Now dislike (should add)
        req_dis = self.factory.post(f"/posts/{self.post.id}/dislike/", data=b"{}", content_type="application/json")
        req_dis.user = self.other
        resp3 = PostInteractionView.as_view()(req_dis, post_id=self.post.id, action="dislike")
        self.assertEqual(resp3.status_code, 200)
        d3 = self._get_json_response(resp3)
        self.assertEqual(d3["action"], "added")
        self.assertEqual(d3["user_interaction"], "dislike")
        self.assertEqual(self.post.dislikes_count, 1)

        # Change from dislike -> like (update existing interaction)
        req_change = self.factory.post(f"/posts/{self.post.id}/like/", data=b"{}", content_type="application/json")
        req_change.user = self.other
        resp4 = PostInteractionView.as_view()(req_change, post_id=self.post.id, action="like")
        self.assertEqual(resp4.status_code, 200)
        d4 = self._get_json_response(resp4)
        # Depending on implementation, action may be 'changed' (we assert semantics)
        self.assertIn(d4["action"], ("changed", "added"))
        self.assertEqual(d4["user_interaction"], "like")
        self.assertEqual(self.post.likes_count, 1)

    def test_share_and_report(self):
        """Test share increments shares_count dan report membuat entri Report."""
        # share
        req_share = self.factory.post(f"/posts/{self.post.id}/share/", data=b"{}", content_type="application/json")
        req_share.user = self.other
        resp_share = PostInteractionView.as_view()(req_share, post_id=self.post.id, action="share")
        self.assertEqual(resp_share.status_code, 200)
        d_share = self._get_json_response(resp_share)
        self.assertEqual(d_share["status"], "success")
        # shares_count properti membaca PostShare related manager
        self.assertEqual(self.post.shares.count(), 1)

        # report
        report_payload = {"category": "SPAM", "description": "Spam content"}
        req_report = self.factory.post(f"/posts/{self.post.id}/report/", data=json.dumps(report_payload), content_type="application/json")
        req_report.user = self.other
        resp_report = PostInteractionView.as_view()(req_report, post_id=self.post.id, action="report")
        self.assertEqual(resp_report.status_code, 200)
        d_report = self._get_json_response(resp_report)
        self.assertEqual(d_report["status"], "success")
        # Pastikan Report dibuat
        r = Report.objects.get(id=d_report["report_id"])
        self.assertEqual(r.reporter, self.other)
        self.assertEqual(r.post, self.post)
