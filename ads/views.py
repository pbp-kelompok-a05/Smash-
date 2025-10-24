from ads.forms import AdForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Ad

def is_superuser(user):
    return user.is_superuser

@user_passes_test(lambda u: u.is_superuser, login_url='/admin-login/')
def manage_ads(request):
    ads = Ad.objects.all().order_by('-created_at')

    # handle form submission
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            ad = form.save()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                html = render_to_string("ads/partials/ad_card.html", {"ad": ad})
                return JsonResponse({"success": True, "html": html})
            return redirect('manage_ads')
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    else:
        form = AdForm()

    return render(request, 'manage_ads.html', {'ads': ads, 'form': form})

@user_passes_test(lambda u: u.is_superuser, login_url='/admin-login/')
def delete_ad(request, ad_id):
    ad = get_object_or_404(Ad, id=ad_id)
    if request.method == "POST":
        ad.delete()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        return redirect("manage_ads")
    return JsonResponse({"success": False})

def admin_login(request):
    """Login khusus untuk admin/superuser sebelum ke halaman kelola iklan."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect("manage_ads")
        else:
            messages.error(request, "Username atau password salah, atau kamu bukan admin.")
    
    return render(request, "admin_login.html")

@user_passes_test(lambda u: u.is_superuser, login_url=reverse_lazy('admin-login'))
def edit_ad(request, ad_id):
    ad = get_object_or_404(Ad, id=ad_id)
    if request.method == "POST":
        form = AdForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            ad = form.save()
            html = render_to_string("ads/partials/ad_card.html", {"ad": ad})
            return JsonResponse({"success": True, "id": ad.id, "html": html})
    return JsonResponse({"success": False})

@user_passes_test(lambda u: u.is_superuser)
def toggle_ad(request, ad_id):
    ad = get_object_or_404(Ad, id=ad_id)
    ad.active = not ad.active
    ad.save()
    return JsonResponse({"success": True, "active": ad.active})