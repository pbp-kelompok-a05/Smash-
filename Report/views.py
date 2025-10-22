import datetime
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core import serializers
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

# Import yang benar untuk model dan form
from .models import Report
from .forms import ReportForm

@login_required
def report_list(request):
    """Menampilkan semua laporan dalam format HTML"""
    reports = Report.objects.all().order_by('-created_at')
    return render(request, 'report_list.html', {'reports': reports})

@login_required
def report_detail(request, report_id):
    """Menampilkan detail laporan tertentu"""
    report = get_object_or_404(Report, pk=report_id)
    return render(request, 'report_detail.html', {'report': report})

@csrf_exempt
@login_required
@require_http_methods(["POST", "GET"])
def create_report(request):
    """Fungsi untuk membuat laporan baru"""
    if request.method == "POST":
        form = ReportForm(request.POST)
        if form.is_valid():
            report_entry = form.save(commit=False)
            report_entry.user = request.user  # Assign user yang login
            report_entry.save()
            messages.success(request, 'Laporan berhasil dibuat!')
            
            # Jika request AJAX, kembalikan JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Laporan berhasil dibuat',
                    'report_id': report_entry.id
                })
            return redirect('report_list')
        else:
            # Handle form tidak valid
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'errors': form.errors
                }, status=400)
    else:
        form = ReportForm()
    
    return render(request, 'create_report.html', {'form': form})

# Fungsi untuk XML dan JSON - PERBAIKAN: Nama fungsi diperbaiki
def show_json(request):
    """Mengembalikan semua laporan dalam format JSON"""
    report_list = Report.objects.all().order_by('-created_at')
    json_data = serializers.serialize("json", report_list)
    return HttpResponse(json_data, content_type="application/json")

def show_xml(request):
    """Mengembalikan semua laporan dalam format XML"""
    report_list = Report.objects.all().order_by('-created_at')
    xml_data = serializers.serialize("xml", report_list)
    return HttpResponse(xml_data, content_type="application/xml")

def show_json_by_id(request, report_id):
    """Mengembalikan laporan tertentu dalam format JSON"""
    try:
        report = Report.objects.get(pk=report_id)
        json_data = serializers.serialize("json", [report])
        return HttpResponse(json_data, content_type="application/json")
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Laporan tidak ditemukan'}, status=404)

def show_xml_by_id(request, report_id):
    """Mengembalikan laporan tertentu dalam format XML"""
    try:
        report = Report.objects.get(pk=report_id)
        xml_data = serializers.serialize("xml", [report])
        return HttpResponse(xml_data, content_type="application/xml")
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Laporan tidak ditemukan'}, status=404)