from django.shortcuts import render
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as auth_logout

@csrf_exempt
def login(request):
    # Normalize username to lower-case to make login case-insensitive.
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            auth_login(request, user)
            # Login status successful.
            return JsonResponse({
                "username": user.username,
                "status": True,
                "message": "Login successful!"
                # Add other data if you want to send data to Flutter.
            }, status=200)
        else:
            return JsonResponse({
                "status": False,
                "message": "Login failed, account is disabled."
            }, status=401)

    else:
        return JsonResponse({
            "status": False,
            "message": "Login failed, please check your username or password."
        }, status=401)

@csrf_exempt
def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Normalize username to lower-case to keep registrations case-insensitive.
        username = data['username']
        password1 = data['password1']
        password2 = data['password2']

        # Check if the passwords match
        if password1 != password2:
            return JsonResponse({
                "status": False,
                "message": "Passwords do not match."
            }, status=400)
        
        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username already exists."
            }, status=400)
        
        # Create the new user
        user = User.objects.create_user(username=username, password=password1)
        user.save()
        
        return JsonResponse({
            "username": user.username,
            "status": 'success',
            "message": "User created successfully!"
        }, status=200)
    
    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=400)

@csrf_exempt
def logout(request):
    username = request.user.username
    try:
        auth_logout(request)
        return JsonResponse({
            "username": username,
            "status": True,
            "message": "Logged out successfully!"
        }, status=200)
    except:
        return JsonResponse({
            "status": False,
            "message": "Logout failed."
        }, status=401)
    
@csrf_exempt
def change_password(request):
    if request.method != 'POST':
        return JsonResponse({"status": False, "message": "Invalid request method."}, status=400)

    # coba parse JSON, jika gagal fallback ke request.POST
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    
    username = data.get('username')
    old_password = data.get('old_password')
    new_password1 = data.get('new_password1') or data.get('new_password')
    new_password2 = data.get('new_password2') or data.get('confirm_password')

    if not all([username, old_password, new_password1, new_password2]):
        return JsonResponse({"status": False, "message": "Missing required fields."}, status=400)
    
    if new_password1 != new_password2:
        return JsonResponse({"status": False, "message": "New passwords do not match."}, status=400)
    
    user = authenticate(username=username, password=old_password)
    if user is None:
        return JsonResponse({"status": False, "message": "Authentication failed. Wrong username or password."}, status=401)
    
    if not user.is_active:
        return JsonResponse({"status": False, "message": "Account is disabled."}, status=403)
    
    user.set_password(new_password1)
    user.save()
    return JsonResponse({"status": True, "message": "Password changed successfully."}, status=200)

@csrf_exempt
def delete_account(request):
    if request.method != 'POST':
        return JsonResponse({"status": False, "message": "Invalid request method."}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()  # fallback ke form-encoded  

    username = data.get('username')
    password = data.get('password')

    if not all([username, password]):
        return JsonResponse({"status": False, "message": "Missing required fields."}, status=400)
    
    user = authenticate(username=username, password=password)
    if user is None:
        return JsonResponse({"status": False, "message": "Authentication failed. Wrong username or password."}, status=401)

    try:
        auth_logout(request)
    except Exception:
        pass
    
    user.delete()
    return JsonResponse({"status": True, "message": "Account deleted successfully."}, status=200)
