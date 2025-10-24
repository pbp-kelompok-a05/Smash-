from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib import messages
from .models import Report
from .forms import ReportForm

def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_staff or user.is_superuser

@login_required
@require_http_methods(["POST"])
@csrf_exempt  # Untuk AJAX, bisa diganti dengan CSRF token di header
def create_report(request):
    """
    AJAX view untuk membuat laporan baru
    Expected POST data: content_type, content_id, category, description
    """
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    report = form.save(commit=False)
                    report.reporter = request.user
                    report.save()
                    
                return JsonResponse({
                    'status': 'success',
                    'message': 'Laporan berhasil dikirim. Terima kasih!',
                    'report_id': report.id
                })
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Terjadi kesalahan: {str(e)}'
                }, status=500)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Data tidak valid',
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Method tidak diizinkan'
    }, status=405)

@login_required
@user_passes_test(is_admin)
def report_list(request):
    """
    View untuk admin melihat daftar laporan
    Support filter by status dan pagination
    """
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    reports = Report.objects.all()
    
    # Filter berdasarkan status
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    # Filter berdasarkan kategori
    if category_filter:
        reports = reports.filter(category=category_filter)
    
    # Pagination
    paginator = Paginator(reports, 20)  # 20 laporan per halaman
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': Report.STATUS_CHOICES,
        'category_choices': Report.CATEGORY_CHOICES,
        'current_status': status_filter,
        'current_category': category_filter,
    }
    
    return render(request, 'report/report_list.html', context)

@login_required
@user_passes_test(is_admin)
def report_detail(request, report_id):
    """
    View untuk admin melihat detail laporan
    """
    report = get_object_or_404(Report, id=report_id)
    
    context = {
        'report': report,
    }
    
    return render(request, 'report/report_detail.html', context)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
@csrf_exempt
def update_report_status(request, report_id):
    """
    AJAX view untuk update status laporan oleh admin
    Expected POST data: status, handled_by (optional)
    """
    report = get_object_or_404(Report, id=report_id)
    
    new_status = request.POST.get('status')
    handled_by = request.POST.get('handled_by', request.user.id)
    
    if new_status not in dict(Report.STATUS_CHOICES):
        return JsonResponse({
            'status': 'error',
            'message': 'Status tidak valid'
        }, status=400)
    
    try:
        with transaction.atomic():
            report.status = new_status
            report.handled_by = request.user
            report.save()
            
            # Jika status bukan pending, set handled_at
            if new_status != 'pending':
                from django.utils import timezone
                report.handled_at = timezone.now()
                report.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Status laporan berhasil diperbarui',
            'new_status': report.get_status_display(),
            'handled_by': report.handled_by.get_full_name() or report.handled_by.username,
            'handled_at': report.handled_at.strftime('%d-%m-%Y %H:%M') if report.handled_at else ''
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["DELETE", "POST"])
@csrf_exempt
def delete_report(request, report_id):
    """
    AJAX view untuk menghapus laporan oleh admin
    Support DELETE dan POST method
    """
    report = get_object_or_404(Report, id=report_id)
    
    try:
        report_id = report.id
        report.delete()
        
        if request.method == 'DELETE':
            return JsonResponse({
                'status': 'success',
                'message': f'Laporan #{report_id} berhasil dihapus'
            })
        else:
            messages.success(request, f'Laporan #{report_id} berhasil dihapus')
            return redirect('report_list')
            
    except Exception as e:
        if request.method == 'DELETE':
            return JsonResponse({
                'status': 'error',
                'message': f'Terjadi kesalahan: {str(e)}'
            }, status=500)
        else:
            messages.error(request, f'Terjadi kesalahan: {str(e)}')
            return redirect('report_detail', report_id=report_id)

@login_required
def my_reports(request):
    """
    View untuk user melihat laporan yang mereka buat
    """
    reports = Report.objects.filter(reporter=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reports, 10)  # 10 laporan per halaman
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'report/my_reports.html', context)

@login_required
@user_passes_test(is_admin)
def report_dashboard(request):
    """
    Dashboard untuk admin dengan statistik laporan
    """
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Statistik umum
    total_reports = Report.objects.count()
    pending_reports = Report.objects.filter(status='pending').count()
    under_review_reports = Report.objects.filter(status='under_review').count()
    
    # Statistik berdasarkan kategori
    category_stats = Report.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Statistik 7 hari terakhir
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_reports = Report.objects.filter(
        created_at__gte=seven_days_ago
    ).values('created_at__date').annotate(
        count=Count('id')
    ).order_by('created_at__date')
    
    context = {
        'total_reports': total_reports,
        'pending_reports': pending_reports,
        'under_review_reports': under_review_reports,
        'category_stats': category_stats,
        'recent_reports': list(recent_reports),
    }
    
    return render(request, 'report/dashboard.html', context)