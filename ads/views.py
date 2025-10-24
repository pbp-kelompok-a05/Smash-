from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages

from ads.forms import AdForm
from .models import Advertisement

# Create your views here.
def is_superuser(user):
    return user.is_superuser

@user_passes_test(lambda u: u.is_superuser, login_url='/admin-login/')
def manage_ads(request):
    ads = Advertisement.objects.all().order_by('-created_at')

    # handle form submission
    if request.method == 'POST':
        form = AdForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('manage_ads')
    else:
        form = AdForm()

    return render(request, 'manage_ads.html', {'ads': ads, 'form': form})

@user_passes_test(lambda u: u.is_superuser, login_url='/admin-login/')
def delete_ad(request, ad_id):
    Ad.objects.filter(id=ad_id).delete()
    return redirect('manage_ads')

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
            form.save()
            return redirect('manage_ads')
    else:
        form = AdForm(instance=ad)

    return render(request, 'edit.html', {'form': form, 'ad': ad})

