# authentication/views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

def login_register_view(request):
    # Jika user sudah login, redirect ke main page
    if request.user.is_authenticated:
        return redirect('main:home')
    return render(request, "account/login_register.html")

def register_ajax(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return JsonResponse({
                "success": True, 
                "username": user.username,
                "redirect_url": reverse('main:home')  # Redirect ke halaman main
            })
        return JsonResponse({
            "success": False, 
            "errors": form.errors
        }, status=400)
    return JsonResponse({
        "error": "Invalid method"
    }, status=405)

def login_ajax(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return JsonResponse({
                "success": True, 
                "username": user.username,
                "redirect_url": reverse('main:home')  # Redirect ke halaman main
            })
        return JsonResponse({
            "success": False, 
            "errors": form.errors
        }, status=400)
    return JsonResponse({
        "error": "Invalid method"
    }, status=405)

def logout_ajax(request):
    if request.method == "POST":
        logout(request)
        return JsonResponse({
            "success": True,
            "redirect_url": reverse('account:login_register')  # Redirect kembali ke login
        })
    return JsonResponse({
        "error": "Invalid method"
    }, status=405)