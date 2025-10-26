from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User

from .models import Advertisement
from .forms import AdForm


def get_test_image():
    # 1x1 px gif
    small_gif = (
        b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
        b"\xff\xff\xff!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )
    return SimpleUploadedFile("test.gif", small_gif, content_type="image/gif")


class AdvertisementModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("admin", "admin@example.com", "pass")

    def test_inline_normalizes_delay_to_zero(self):
        ad = Advertisement.objects.create(
            title="Inline Ad",
            description="",
            image=None,
            link="https://example.com",
            ad_type="inline",
            popup_delay_seconds=10,
            owner=self.owner,
        )
        ad.refresh_from_db()
        self.assertEqual(ad.popup_delay_seconds, 0)

    def test_popup_keeps_delay(self):
        ad = Advertisement.objects.create(
            title="Popup Ad",
            description="",
            image=None,
            link="https://example.com",
            ad_type="popup",
            popup_delay_seconds=7,
            owner=self.owner,
        )
        ad.refresh_from_db()
        self.assertEqual(ad.popup_delay_seconds, 7)


class AdFormTests(TestCase):
    def test_inline_delay_not_required_and_normalized(self):
        form = AdForm(
            data={
                "title": "Inline",
                "description": "",
                "link": "https://example.com",
                "ad_type": "inline",
                # popup_delay_seconds omitted on purpose
                "is_active": True,
            },
            files={"image": get_test_image()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data.get("popup_delay_seconds"), 0)

    def test_popup_delay_required(self):
        form = AdForm(
            data={
                "title": "Popup",
                "description": "",
                "link": "https://example.com",
                "ad_type": "popup",
                # popup_delay_seconds missing -> should error
                "is_active": True,
            },
            files={"image": get_test_image()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("popup_delay_seconds", form.errors)


class AdvertisementAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser("root", "root@example.com", "pass")
        self.client.login(username="root", password="pass")

    def test_create_inline_ad_via_api(self):
        url = reverse("ad_list")  # /ads/api/
        resp = self.client.post(
            url,
            data={
                "title": "Inline API",
                "description": "",
                "link": "https://example.com",
                "ad_type": "inline",
                # omit delay
                "is_active": True,
            },
            follow=True,
            FILES={"image": get_test_image()},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        ad = Advertisement.objects.order_by("-id").first()
        self.assertEqual(ad.popup_delay_seconds, 0)
        self.assertEqual(ad.owner, self.superuser)

    def test_list_and_detail_api(self):
        ad = Advertisement.objects.create(
            title="Popup",
            description="",
            image=None,
            link="https://example.com/x",
            ad_type="popup",
            popup_delay_seconds=3,
            owner=self.superuser,
        )
        list_url = reverse("ad_list")
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        ids = [a["id"] for a in payload.get("ads", [])]
        self.assertIn(ad.id, ids)

        detail_url = reverse("ad_detail", kwargs={"ad_id": ad.id})
        resp2 = self.client.get(detail_url)
        self.assertEqual(resp2.status_code, 200)
        detail = resp2.json()
        self.assertEqual(detail.get("id"), ad.id)
        self.assertEqual(detail.get("popup_delay_seconds"), 3)

    def test_update_and_delete_api(self):
        ad = Advertisement.objects.create(
            title="To Update",
            description="",
            image=None,
            link="https://example.com/y",
            ad_type="popup",
            popup_delay_seconds=1,
            owner=self.superuser,
        )
        update_url = reverse("ad_update", kwargs={"ad_id": ad.id})
        resp = self.client.post(update_url, data={
            "title": "Updated",
            "description": "desc",
            "link": "https://example.com/z",
            "ad_type": "popup",
            "popup_delay_seconds": 9,
            "is_active": True,
        })
        self.assertEqual(resp.status_code, 200)
        ad.refresh_from_db()
        self.assertEqual(ad.title, "Updated")
        self.assertEqual(ad.popup_delay_seconds, 9)

        delete_url = reverse("ad_detail", kwargs={"ad_id": ad.id})
        resp2 = self.client.delete(delete_url)
        self.assertEqual(resp2.status_code, 200)
        self.assertFalse(Advertisement.objects.filter(id=ad.id).exists())
