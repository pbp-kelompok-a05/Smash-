from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import render


def login_register_view(request):
    return render(request, "login_register.html")


def register_ajax(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return JsonResponse({"success": True, "username": user.username})
        return JsonResponse({"success": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Invalid method"}, status=405)


def login_ajax(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return JsonResponse({"success": True, "username": user.username})
        return JsonResponse({"success": False, "errors": form.errors}, status=400)
    return JsonResponse({"error": "Invalid method"}, status=405)


def logout_ajax(request):
    if request.method == "POST":
        logout(request)
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid method"}, status=405)
