import json
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.core import serializers
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta

# Import models dan forms
from .models import Report, ReportSettings
from .forms import ReportForm, ReportAdminForm, ReportSearchForm, ReportSettingsForm


# ==================== UTILITY FUNCTIONS ====================

def _get_ajax_response(request, template_name, context=None):
    """
    Utility function untuk render AJAX response sebagai modal
    
    Args:
        request: HttpRequest object
        template_name: String path ke template
        context: Dictionary context data
    
    Returns:
        JsonResponse dengan modal HTML
    """
    if context is None:
        context = {}
    
    rendered_html = render(request, template_name, context).content.decode('utf-8')
    return JsonResponse({'modal_html': rendered_html})


def _get_report_data(report):
    """
    Utility function untuk serialize report data
    
    Args:
        report: Report instance
    
    Returns:
        Dictionary dengan data report yang terserialisasi
    """
    return {
        'id': str(report.id),
        'reporter': report.reporter_display_name,
        'reporter_id': report.reporter.id,
        'reported_object_type': report.get_reported_content_type(),
        'reported_object_id': str(report.object_id),
        'reported_content_preview': report.get_reported_content_preview(),
        'reason': report.get_reason_display(),
        'reason_value': report.reason,
        'description': report.description,
        'status': report.get_status_display(),
        'status_value': report.status,
        'is_anonymous': report.is_anonymous,
        'evidence_image_url': report.evidence_image.url if report.evidence_image else None,
        'evidence_url': report.evidence_url,
        'created_at': report.created_at.strftime('%d %b %Y, %H:%M'),
        'updated_at': report.updated_at.strftime('%d %b %Y, %H:%M'),
        'resolved_at': report.resolved_at.strftime('%d %b %Y, %H:%M') if report.resolved_at else None,
        'resolved_by': report.resolved_by.username if report.resolved_by else None,
        'admin_notes': report.admin_notes,
        'action_taken': report.action_taken,
        'is_resolved': report.is_resolved,
        'is_pending': report.is_pending,
        'days_since_created': report.days_since_created,
        'detail_url': reverse('report_detail', kwargs={'pk': report.id}),
        'can_edit': report.can_edit(report.reporter),  # Untuk pemilik laporan
        'can_delete': report.can_delete(report.reporter),  # Untuk pemilik laporan
    }


def is_staff_user(user):
    """
    Check jika user adalah staff atau superuser
    
    Args:
        user: User instance
    
    Returns:
        Boolean True jika staff/superuser
    """
    return user.is_staff or user.is_superuser


# ==================== REPORT CRUD VIEWS ====================

@login_required
def report_list(request):
    """
    Menampilkan daftar laporan dengan filter dan pencarian
    
    Features:
    - Filter by status dan reason
    - Pencarian berdasarkan deskripsi dan pelapor
    - AJAX pagination
    - Different views untuk user dan admin
    
    Args:
        request: HttpRequest object
    
    Returns:
        HttpResponse dengan template report_list.html
    """
    try:
        # Tentukan queryset berdasarkan user role
        if is_staff_user(request.user):
            # Admin bisa lihat semua laporan
            reports = Report.objects.all().select_related('reporter', 'resolved_by')
        else:
            # User biasa hanya bisa lihat laporan mereka sendiri
            reports = Report.objects.filter(reporter=request.user).select_related('reporter', 'resolved_by')
        
        # Apply filters
        filter_form = ReportSearchForm(request.GET)
        if filter_form.is_valid():
            status = filter_form.cleaned_data.get('status')
            reason = filter_form.cleaned_data.get('reason')
            date_from = filter_form.cleaned_data.get('date_from')
            date_to = filter_form.cleaned_data.get('date_to')
            search = filter_form.cleaned_data.get('search')
            
            if status:
                reports = reports.filter(status=status)
            if reason:
                reports = reports.filter(reason=reason)
            if date_from:
                reports = reports.filter(created_at__date__gte=date_from)
            if date_to:
                reports = reports.filter(created_at__date__lte=date_to)
            if search:
                reports = reports.filter(
                    Q(description__icontains=search) |
                    Q(reporter__username__icontains=search) |
                    Q(admin_notes__icontains=search)
                )
        
        # Ordering
        reports = reports.order_by('-created_at')
        
        # AJAX pagination request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            page = int(request.GET.get('page', 1))
            per_page = 10
            start = (page - 1) * per_page
            end = start + per_page
            
            paginated_reports = reports[start:end]
            reports_data = [_get_report_data(report) for report in paginated_reports]
            
            return JsonResponse({
                'status': 'success',
                'reports': reports_data,
                'has_next': len(paginated_reports) == per_page,
                'next_page': page + 1
            })
        
        # Statistik untuk admin
        stats = {}
        if is_staff_user(request.user):
            stats = {
                'total_reports': reports.count(),
                'pending_reports': reports.filter(status=Report.STATUS_PENDING).count(),
                'resolved_reports': reports.filter(status=Report.STATUS_RESOLVED).count(),
                'rejected_reports': reports.filter(status=Report.STATUS_REJECTED).count(),
            }
        
        context = {
            'reports': reports[:20],  # Initial load 20 reports
            'filter_form': filter_form,
            'stats': stats,
            'is_staff': is_staff_user(request.user),
            'load_more_url': reverse('report_list') + '?ajax=1&'
        }
        
        return render(request, 'reports/report_list.html', context)
    
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return render(request, 'reports/report_list.html', {
            'reports': Report.objects.none(),
            'is_staff': is_staff_user(request.user)
        })


@login_required
def report_detail(request, pk):
    """
    Menampilkan detail laporan
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        HttpResponse dengan template report_detail.html atau JsonResponse untuk AJAX
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        
        # Permission check
        if not report.can_view(request.user):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Anda tidak memiliki izin untuk melihat laporan ini.'
                }, status=403)
            messages.error(request, 'Anda tidak memiliki izin untuk melihat laporan ini.')
            return redirect('report_list')
        
        # AJAX request untuk data report saja
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            report_data = _get_report_data(report)
            report_data.update({
                'can_edit': report.can_edit(request.user),
                'can_delete': report.can_delete(request.user),
                'can_resolve': report.can_resolve(request.user),
            })
            
            return JsonResponse({
                'status': 'success',
                'report': report_data
            })
        
        context = {
            'report': report,
            'can_edit': report.can_edit(request.user),
            'can_delete': report.can_delete(request.user),
            'can_resolve': report.can_resolve(request.user),
        }
        return render(request, 'reports/report_detail.html', context)
        
    except Report.DoesNotExist:
        error_msg = 'Laporan tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('report_list')


@login_required
@csrf_exempt
@require_http_methods(["POST", "GET"])
def create_report(request, content_type_id=None, object_id=None):
    """
    Membuat laporan baru untuk konten tertentu
    
    Args:
        request: HttpRequest object
        content_type_id: ID content type (opsional, bisa dari URL)
        object_id: UUID object yang dilaporkan (opsional, bisa dari URL)
    
    Returns:
        JsonResponse untuk AJAX atau HttpResponse redirect
    """
    # Get reported object dari parameter atau POST data
    reported_object = None
    if request.method == "POST":
        content_type_id = request.POST.get('content_type_id') or content_type_id
        object_id = request.POST.get('object_id') or object_id
    
    if content_type_id and object_id:
        try:
            content_type = ContentType.objects.get_for_id(content_type_id)
            reported_object = content_type.get_object_for_this_type(pk=object_id)
        except (ContentType.DoesNotExist, Exception):
            reported_object = None
    
    if request.method == "POST":
        form = ReportForm(
            request.POST, 
            request.FILES, 
            reporter=request.user,
            reported_object=reported_object
        )
        
        if form.is_valid():
            try:
                report = form.save()
                
                # AJAX response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Laporan berhasil dibuat! Terima kasih telah membantu menjaga komunitas.',
                        'report': _get_report_data(report),
                        'redirect_url': reverse('report_detail', kwargs={'pk': report.id})
                    })
                
                messages.success(request, 'Laporan berhasil dibuat! Terima kasih telah membantu menjaga komunitas.')
                return redirect('report_detail', pk=report.id)
                
            except Exception as e:
                error_msg = f'Terjadi kesalahan saat menyimpan laporan: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=500)
                messages.error(request, error_msg)
        else:
            # AJAX response dengan error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Terjadi kesalahan validasi. Silakan periksa form Anda.',
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
    else:
        form = ReportForm(reporter=request.user, reported_object=reported_object)
    
    # AJAX GET request - return modal HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return _get_ajax_response(
            request, 
            'reports/modals/report_create_modal.html', 
            {
                'form': form, 
                'reported_object': reported_object,
                'action_url': reverse('create_report')
            }
        )
    
    return render(request, 'reports/report_form.html', {
        'form': form,
        'reported_object': reported_object,
        'title': 'Buat Laporan Baru'
    })


@login_required
def update_report(request, pk):
    """
    Mengupdate laporan (hanya untuk laporan pending milik user)
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        JsonResponse untuk AJAX atau HttpResponse redirect
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        
        # Permission check
        if not report.can_edit(request.user):
            error_msg = 'Anda tidak memiliki izin untuk mengedit laporan ini.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                }, status=403)
            messages.error(request, error_msg)
            return redirect('report_detail', pk=pk)
        
        if request.method == "POST":
            form = ReportForm(
                request.POST, 
                request.FILES, 
                instance=report,
                reporter=request.user,
                reported_object=report.reported_object
            )
            
            if form.is_valid():
                try:
                    updated_report = form.save()
                    
                    # AJAX response
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Laporan berhasil diupdate!',
                            'report': _get_report_data(updated_report),
                            'redirect_url': reverse('report_detail', kwargs={'pk': updated_report.id})
                        })
                    
                    messages.success(request, 'Laporan berhasil diupdate!')
                    return redirect('report_detail', pk=report.id)
                    
                except Exception as e:
                    error_msg = f'Terjadi kesalahan saat mengupdate laporan: {str(e)}'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'error',
                            'message': error_msg
                        }, status=500)
                    messages.error(request, error_msg)
            else:
                # AJAX response dengan error
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Terjadi kesalahan validasi.',
                        'errors': form.errors
                    }, status=400)
                
                messages.error(request, 'Terjadi kesalahan. Silakan periksa form Anda.')
        else:
            form = ReportForm(
                instance=report,
                reporter=request.user,
                reported_object=report.reported_object
            )
        
        # AJAX GET request - return modal HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return _get_ajax_response(
                request,
                'reports/modals/report_form_modal.html',
                {
                    'form': form, 
                    'report': report,
                    'action_url': reverse('update_report', kwargs={'pk': pk})
                }
            )
        
        return render(request, 'reports/report_form.html', {
            'form': form,
            'report': report,
            'title': 'Edit Laporan'
        })
        
    except Report.DoesNotExist:
        error_msg = 'Laporan tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('report_list')


@login_required
def delete_report(request, pk):
    """
    Menghapus laporan (soft delete belum diimplementasikan, bisa ditambahkan)
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        JsonResponse untuk AJAX atau HttpResponse redirect
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        
        # Permission check
        if not report.can_delete(request.user):
            error_msg = 'Anda tidak memiliki izin untuk menghapus laporan ini.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                }, status=403)
            messages.error(request, error_msg)
            return redirect('report_detail', pk=pk)
        
        if request.method == "POST":
            try:
                report_title = str(report)
                report.delete()
                
                # AJAX response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Laporan berhasil dihapus!',
                        'redirect_url': reverse('report_list')
                    })
                
                messages.success(request, f'Laporan "{report_title}" berhasil dihapus!')
                return redirect('report_list')
                
            except Exception as e:
                error_msg = f'Terjadi kesalahan saat menghapus laporan: {str(e)}'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=500)
                messages.error(request, error_msg)
        
        # AJAX GET request - return confirmation modal HTML
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return _get_ajax_response(
                request,
                'reports/modals/report_confirm_delete_modal.html',
                {'report': report}
            )
        
        return render(request, 'reports/report_confirm_delete.html', {'report': report})
        
    except Report.DoesNotExist:
        error_msg = 'Laporan tidak ditemukan.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=404)
        messages.error(request, error_msg)
        return redirect('report_list')


# ==================== REPORT ADMIN ACTIONS ====================

@user_passes_test(is_staff_user)
@login_required
def admin_report_list(request):
    """
    View khusus admin untuk mengelola laporan
    
    Args:
        request: HttpRequest object
    
    Returns:
        HttpResponse dengan template admin_report_list.html
    """
    try:
        reports = Report.objects.all().select_related('reporter', 'resolved_by')
        
        # Filter untuk admin
        filter_form = ReportSearchForm(request.GET)
        if filter_form.is_valid():
            status = filter_form.cleaned_data.get('status')
            reason = filter_form.cleaned_data.get('reason')
            date_from = filter_form.cleaned_data.get('date_from')
            date_to = filter_form.cleaned_data.get('date_to')
            search = filter_form.cleaned_data.get('search')
            
            if status:
                reports = reports.filter(status=status)
            if reason:
                reports = reports.filter(reason=reason)
            if date_from:
                reports = reports.filter(created_at__date__gte=date_from)
            if date_to:
                reports = reports.filter(created_at__date__lte=date_to)
            if search:
                reports = reports.filter(
                    Q(description__icontains=search) |
                    Q(reporter__username__icontains=search) |
                    Q(admin_notes__icontains=search)
                )
        
        # Ordering untuk admin: pending first
        reports = reports.order_by('status', '-created_at')
        
        # Statistik
        stats = {
            'total_reports': reports.count(),
            'pending_reports': reports.filter(status=Report.STATUS_PENDING).count(),
            'under_review': reports.filter(status=Report.STATUS_UNDER_REVIEW).count(),
            'resolved_reports': reports.filter(status=Report.STATUS_RESOLVED).count(),
            'rejected_reports': reports.filter(status=Report.STATUS_REJECTED).count(),
        }
        
        context = {
            'reports': reports,
            'filter_form': filter_form,
            'stats': stats,
            'is_staff': True
        }
        
        return render(request, 'reports/admin_report_list.html', context)
        
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return render(request, 'reports/admin_report_list.html', {
            'reports': Report.objects.none(),
            'is_staff': True
        })


@user_passes_test(is_staff_user)
@login_required
@require_http_methods(["POST"])
def mark_report_reviewed(request, pk):
    """
    Menandai laporan sedang ditinjau (admin action)
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        JsonResponse dengan hasil action
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        report.mark_as_reviewed(user=request.user)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Laporan ditandai sedang ditinjau.',
            'report': _get_report_data(report)
        })
        
    except Report.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Laporan tidak ditemukan.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@user_passes_test(is_staff_user)
@login_required
@require_http_methods(["POST"])
def resolve_report(request, pk):
    """
    Menyelesaikan laporan (admin action)
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        JsonResponse dengan hasil action
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        
        action_taken = request.POST.get('action_taken', '')
        admin_notes = request.POST.get('admin_notes', '')
        
        report.resolve(
            user=request.user,
            notes=admin_notes,
            action_taken=action_taken
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Laporan berhasil diselesaikan.',
            'report': _get_report_data(report)
        })
        
    except Report.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Laporan tidak ditemukan.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@user_passes_test(is_staff_user)
@login_required
@require_http_methods(["POST"])
def reject_report(request, pk):
    """
    Menolak laporan (admin action)
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        JsonResponse dengan hasil action
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        
        admin_notes = request.POST.get('admin_notes', '')
        
        report.reject(
            user=request.user,
            notes=admin_notes
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Laporan berhasil ditolak.',
            'report': _get_report_data(report)
        })
        
    except Report.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Laporan tidak ditemukan.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


@user_passes_test(is_staff_user)
@login_required
@require_http_methods(["POST"])
def reopen_report(request, pk):
    """
    Membuka kembali laporan yang telah ditutup (admin action)
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        JsonResponse dengan hasil action
    """
    try:
        report = get_object_or_404(Report, pk=pk)
        report.reopen()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Laporan berhasil dibuka kembali.',
            'report': _get_report_data(report)
        })
        
    except Report.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Laporan tidak ditemukan.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }, status=500)


# ==================== REPORT SETTINGS ====================

@user_passes_test(is_staff_user)
@login_required
def report_settings(request):
    """
    View untuk mengatur pengaturan sistem pelaporan
    
    Args:
        request: HttpRequest object
    
    Returns:
        HttpResponse dengan template report_settings.html
    """
    try:
        # Get or create settings instance
        settings_instance, created = ReportSettings.objects.get_or_create(pk=1)
        
        if request.method == "POST":
            form = ReportSettingsForm(request.POST, instance=settings_instance)
            if form.is_valid():
                form.save()
                messages.success(request, 'Pengaturan berhasil disimpan!')
                return redirect('report_settings')
        else:
            form = ReportSettingsForm(instance=settings_instance)
        
        context = {
            'form': form,
            'settings': settings_instance
        }
        
        return render(request, 'reports/report_settings.html', context)
        
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan: {str(e)}')
        return render(request, 'reports/report_settings.html', {
            'form': ReportSettingsForm()
        })


# ==================== API VIEWS (JSON/XML) ====================

def show_json(request):
    """
    Mengembalikan semua laporan dalam format JSON
    
    Returns:
        HttpResponse dengan data JSON
    """
    try:
        # Hanya tampilkan laporan yang bisa dilihat user
        if is_staff_user(request.user):
            report_list = Report.objects.all().select_related('reporter', 'resolved_by')
        else:
            report_list = Report.objects.filter(reporter=request.user).select_related('reporter', 'resolved_by')
        
        report_list = report_list.order_by('-created_at')
        json_data = serializers.serialize("json", report_list)
        return HttpResponse(json_data, content_type="application/json")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_xml(request):
    """
    Mengembalikan semua laporan dalam format XML
    
    Returns:
        HttpResponse dengan data XML
    """
    try:
        # Hanya tampilkan laporan yang bisa dilihat user
        if is_staff_user(request.user):
            report_list = Report.objects.all().select_related('reporter', 'resolved_by')
        else:
            report_list = Report.objects.filter(reporter=request.user).select_related('reporter', 'resolved_by')
        
        report_list = report_list.order_by('-created_at')
        xml_data = serializers.serialize("xml", report_list)
        return HttpResponse(xml_data, content_type="application/xml")
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_json_by_id(request, pk):
    """
    Mengembalikan laporan tertentu dalam format JSON
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        HttpResponse dengan data JSON atau JsonResponse error
    """
    try:
        report = Report.objects.select_related('reporter', 'resolved_by').get(pk=pk)
        
        # Permission check
        if not report.can_view(request.user):
            return JsonResponse({'error': 'Anda tidak memiliki izin untuk melihat laporan ini.'}, status=403)
        
        json_data = serializers.serialize("json", [report])
        return HttpResponse(json_data, content_type="application/json")
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Laporan tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def show_xml_by_id(request, pk):
    """
    Mengembalikan laporan tertentu dalam format XML
    
    Args:
        request: HttpRequest object
        pk: UUID dari laporan
    
    Returns:
        HttpResponse dengan data XML atau JsonResponse error
    """
    try:
        report = Report.objects.select_related('reporter', 'resolved_by').get(pk=pk)
        
        # Permission check
        if not report.can_view(request.user):
            return JsonResponse({'error': 'Anda tidak memiliki izin untuk melihat laporan ini.'}, status=403)
        
        xml_data = serializers.serialize("xml", [report])
        return HttpResponse(xml_data, content_type="application/xml")
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Laporan tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)