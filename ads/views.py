import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from .models import Advertisement
from .forms import AdForm, PremiumSubscribeForm
from django.shortcuts import redirect



def is_superuser(user):
    """Cuma boleh diakses superuser."""
    return user.is_superuser


@method_decorator(csrf_exempt, name="dispatch")
class AdvertisementAPI(View):
    """API CRUD Iklan untuk Superuser (AJAX)"""

    def get(self, request, ad_id=None):
        """GET: ambil satu atau semua iklan"""
        if ad_id:
            ad = get_object_or_404(Advertisement, id=ad_id)
            return JsonResponse({
                "id": ad.id,
                "title": ad.title,
                "description": ad.description,
                "image": ad.image.url if ad.image else None,
                "link": ad.link,
                "ad_type": ad.ad_type,
                "popup_delay_seconds": ad.popup_delay_seconds,
                "is_active": ad.is_active,
            })

        ads = Advertisement.objects.all().order_by("-created_at")
        return JsonResponse({
            "ads": [
                {
                    "id": ad.id,
                    "title": ad.title,
                    "link": ad.link,
                    "ad_type": ad.ad_type,
                    "popup_delay_seconds": ad.popup_delay_seconds,
                    "is_active": ad.is_active,
                    "image": ad.image.url if ad.image else None,
                }
                for ad in ads
            ]
        })

    def post(self, request, ad_id=None):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({"status": "forbidden", "message": "Admin only"}, status=403)
        """
        POST:
        - Jika tanpa ad_id → CREATE
        - Jika dengan ad_id → UPDATE
        """
        if ad_id:
            return self.update_ad(request, ad_id)

        # CREATE
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.owner = request.user
            ad.save()
            return JsonResponse({"status": "success", "message": "Iklan berhasil dibuat"})
        return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    def update_ad(self, request, ad_id):
        """UPDATE iklan"""
        ad = get_object_or_404(Advertisement, id=ad_id)
        form = AdForm(request.POST, request.FILES, instance=ad)

        if form.is_valid():
            updated = form.save(commit=False)
            is_active_raw = request.POST.get("is_active")
            if is_active_raw is not None:
                updated.is_active = str(is_active_raw).lower() in {"true", "1", "on", "yes"}
            updated.save()

            return JsonResponse({
                "status": "success",
                "message": "Iklan berhasil diperbarui",
                "ad": {
                    "id": updated.id,
                    "title": updated.title,
                    "description": updated.description,
                    "image": updated.image.url if updated.image else None,
                    "link": updated.link,
                    "ad_type": updated.ad_type,
                    "popup_delay_seconds": updated.popup_delay_seconds,
                    "is_active": updated.is_active,
                },
            })
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    def delete(self, request, ad_id):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return JsonResponse({"status": "forbidden", "message": "Admin only"}, status=403)
        """DELETE: hapus iklan"""
        ad = get_object_or_404(Advertisement, id=ad_id)
        ad.delete()
        return JsonResponse({"status": "success", "message": "Iklan berhasil dihapus"})


@user_passes_test(is_superuser)
def manage_ads_page(request):
    """Halaman dashboard kelola iklan"""
    form = AdForm()
    return render(request, "manage_ads.html", {"form": form})


def redirect_ad(request, ad_id: int):
    ad = get_object_or_404(Advertisement, id=ad_id, is_active=True)
    if not ad.link:
        return redirect("/")
    return redirect(ad.link)


from .models import PremiumSubscriber


def premium_page(request):
    return render(request, "premium.html")


def premium_checkout(request):
    """Page alamat pembayaran premium"""
    # Normally: create checkout session here then redirect to gateway.
    # For demo, just go to success.
    return redirect("ads_premium_success")


def premium_success(request):
    """Page sukses langganan premium"""
    initial_email = request.user.email if request.user.is_authenticated else ""
    form = PremiumSubscribeForm(request.POST or None, initial={"email": initial_email})
    saved = False
    saved_email = None
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        PremiumSubscriber.objects.get_or_create(
            email=email,
            defaults={
                "user": request.user if request.user.is_authenticated else None,
                "payment_reference": "manual",
                "active": True,
            },
        )
        saved = True
        saved_email = email
    return render(request, "premium_success.html", {"form": form, "saved": saved, "saved_email": saved_email})
