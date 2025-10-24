from datetime import datetime
from django.shortcuts import render
from post.views import *

# Penambahan import modul untuk meretriksi akses halaman main dan news detail
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect, get_object_or_404

# Tambahan import untuk mengembalikan data dalam bentuk XML
from django.http import HttpResponse
from django.core import serializers

# Penambahan impor modul untuk form registrasi, login, dan logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

# Penambahan import modul untuk menggunakan data dari cookies
import datetime
from django.http import HttpResponseRedirect
from django.urls import reverse

# Import tambahan untuk menampilkan data di halaman utama dengan AJAX
from django.http import HttpResponseRedirect, JsonResponse

# Import tambahan untuk menangani request AJAX
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Melindungi serangan XSS
from django.utils.html import strip_tags

def show_main(request):
    # Penambahan konfigurasi untuk melakukan filter news yang telah dibuat sebelumnya
    # hal tersebut akan menampilkan halaman utama setelah user login

    return render(request, "main.html")

def login_user(request):
   if request.method == 'POST':
      form = AuthenticationForm(data=request.POST)

      # Konfigurasi untuk menyimpan cookie baru, last_login, yang berisi timestamp terakhir kali user melakukan login 
      if form.is_valid():
            user = form.get_user()
            login(request, user)
            response = HttpResponseRedirect(reverse("main:show_main"))
            response.set_cookie('last_login', str(datetime.datetime.now()))
            return response

   else:
      form = AuthenticationForm(request)
   context = {'form': form}
   return render(request, 'login.html', context)

def register(request):
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been successfully created!')
            return redirect('main:login')
    context = {'form':form}
    return render(request, 'register.html', context)