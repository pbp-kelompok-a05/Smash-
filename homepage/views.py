from django.shortcuts import render
from django.http import JsonResponse

def homepage_view(request):
    return render(request, "homepage-view.html")

def api_feed(request):
    posts = [
        {"user": "Sally", "title": "Behance Connection", "likes": 182, "comments": 21},
        {"user": "Rashika", "title": "Design Hive", "likes": 99, "comments": 7},
    ]
    return JsonResponse({"posts": posts})
