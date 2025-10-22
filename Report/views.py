# Penambahan import untuk implementasi penggunaan data dari cookies
import datetime
from django.http import HttpResponseRedirect
from django.urls import reverse

# Penambahan import modul decorator login_required dari sistem autentikasi milik Django
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect, get_object_or_404

# Penambahan import modul untuk request pengiriman data ke dalam bentuk XML dan JSON
from django.http import HttpResponse
from django.core import serializers

# Penambahan import modul untuk membuat fungsi dan form registrasi serta fungsi login dan logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# Penambahan import untuk AJAX dan JSON response
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

import Report
from Report.forms import ReportForm

# Create your views here.
@csrf_exempt
@login_required
@require_http_methods(["POST"])
# Fungsi untuk membuat laporan 
def create_report(request):
    form = ReportForm(data=request.POST)
    # Cek apakah form yang dimasukkan valid
    if form.is_valid():
        # Menyimpan report_entry dari user
        report_entry = form.save(commit=False)
        report_entry.save()
        context = {'form' : form}
        return render(request, "", context)
    
# Menambahkan fungsi untuk mengirimkan data dalam bentuk JSON dan XML
def show_xml(request):
    report_list = Report.objects.all()
    json_data = serializers.serialize("json", report_list)
    return HttpResponse(json_data, content_type="application/json")

def show_json(request):
    report_list = Report.objects.all()
    xml_data = serializers.serialize("xml", report_list)
    return HttpResponse(xml_data, content_type="application/xml")

# Melakukan filter berdasarkan ID
def show_xml_by_id(request, report_id):
    try:
        report_list = Report.objects.filter(pk=report_id)
        xml_data = serializers.serialize("xml", report_list)
        return HttpResponse(xml_data, content_type="application/xml")
    except Report.DoesNotExist:
        return HttpResponse(status=404)
    
def show_json_by_id(request, report_id):
    try:
        report_list = Report.objects.filter(pk=report_id)
        json_data = serializers.serialize("json", report_list)
        return HttpResponse(json_data, content_type="application/json")
    except Report.DoesNotExist:
        return HttpResponse(status=404)