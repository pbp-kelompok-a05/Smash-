import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Report, ReportSettings
from .forms import ReportForm, ReportAdminForm, ReportSettingsForm


class ReportCreateView(LoginRequiredMixin, View):
    """
    AJAX View untuk membuat laporan baru.
    """
    def post(self, request):
        # Get data from AJAX request
        content_type_id = request.POST.get('content_type_id')
        object_id = request.POST.get('object_id')
        category = request.POST.get('category')
        description = request.POST.get('description', '')

        # Validate required fields
        if not all([content_type_id, object_id, category]):
            return JsonResponse({
                'success': False,
                'message': 'Data yang diperlukan tidak lengkap'
            }, status=400)

        try:
            content_type = ContentType.objects.get(id=content_type_id)
            reported_object = content_type.get_object_for_this_type(id=object_id)
        except (ContentType.DoesNotExist, Exception):
            return JsonResponse({
                'success': False,
                'message': 'Konten yang dilaporkan tidak ditemukan'
            }, status=404)

        # Check if user already reported this object
        existing_report = Report.objects.filter(
            reporter=request.user,
            content_type=content_type,
            object_id=object_id
        ).first()

        if existing_report:
            return JsonResponse({
                'success': False,
                'message': 'Anda sudah melaporkan konten ini sebelumnya'
            }, status=400)

        # Create report
        report = Report.objects.create(
            reporter=request.user,
            content_type=content_type,
            object_id=object_id,
            category=category,
            description=description
        )

        # Check if auto-hide threshold is reached
        settings = ReportSettings.objects.get(pk=1)
        report_count = Report.objects.filter(
            content_type=content_type,
            object_id=object_id,
            status__in=[Report.STATUS_PENDING, Report.STATUS_UNDER_REVIEW]
        ).count()

        auto_hide = False
        if report_count >= settings.auto_action_threshold and settings.auto_hide_on_threshold:
            # Auto hide the content (example implementation)
            if hasattr(reported_object, 'is_hidden'):
                reported_object.is_hidden = True
                reported_object.save()
                auto_hide = True

        return JsonResponse({
            'success': True,
            'message': 'Laporan berhasil dikirim. Tim moderasi akan meninjaunya.',
            'report_id': str(report.id),
            'auto_hide': auto_hide,
            'current_reports': report_count
        })


class ReportListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View untuk menampilkan daftar laporan (hanya admin/staff).
    """
    model = Report
    template_name = 'report/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    ordering = ['-created_at']

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter berdasarkan status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter berdasarkan kategori
        category_filter = self.request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        # Filter berdasarkan konten type
        content_type_filter = self.request.GET.get('content_type')
        if content_type_filter:
            queryset = queryset.filter(content_type__model=content_type_filter)
        
        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(description__icontains=search_query) |
                Q(reporter__username__icontains=search_query) |
                Q(admin_notes__icontains=search_query)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Report.STATUS_CHOICES
        context['category_choices'] = Report.CATEGORY_CHOICES
        context['content_types'] = ContentType.objects.filter(
            model__in=['forumpost', 'comment']
        )
        
        # Stats for dashboard
        context['total_reports'] = Report.objects.count()
        context['pending_reports'] = Report.objects.filter(status=Report.STATUS_PENDING).count()
        context['resolved_reports'] = Report.objects.filter(status=Report.STATUS_RESOLVED).count()
        
        return context


class ReportDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    View untuk melihat detail laporan (hanya admin/staff).
    """
    model = Report
    template_name = 'report/report_detail.html'
    context_object_name = 'report'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()
        
        # Get all reports for the same object
        context['related_reports'] = Report.objects.filter(
            content_type=report.content_type,
            object_id=report.object_id
        ).exclude(id=report.id).order_by('-created_at')
        
        context['total_reports_for_object'] = context['related_reports'].count() + 1
        
        return context


class ReportUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View untuk mengupdate status laporan (hanya admin/staff).
    """
    model = Report
    form_class = ReportAdminForm
    template_name = 'report/report_update.html'
    
    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        report = form.save(commit=False)
        
        # Jika status berubah ke under_review, set reviewed_by dan reviewed_at
        if report.status == Report.STATUS_UNDER_REVIEW and not report.reviewed_by:
            report.reviewed_by = self.request.user
            report.reviewed_at = timezone.now()
        
        # Jika status berubah ke resolved atau rejected, set is_resolved
        if report.status in [Report.STATUS_RESOLVED, Report.STATUS_REJECTED]:
            report.is_resolved = True
            if not report.reviewed_by:
                report.reviewed_by = self.request.user
                report.reviewed_at = timezone.now()
        
        report.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('report:report-detail', kwargs={'pk': self.object.pk})


class ReportDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View untuk menghapus laporan (hanya admin/staff).
    """
    model = Report
    template_name = 'report/report_confirm_delete.html'
    success_url = reverse_lazy('report:report-list')

    def test_func(self):
        return self.request.user.is_staff


# AJAX Views untuk admin actions
class BulkReportActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    AJAX View untuk aksi massal pada laporan.
    """
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request):
        action = request.POST.get('action')
        report_ids = request.POST.getlist('report_ids[]')
        
        if not report_ids:
            return JsonResponse({
                'success': False,
                'message': 'Tidak ada laporan yang dipilih'
            }, status=400)

        reports = Report.objects.filter(id__in=report_ids)
        updated_count = 0

        if action == 'mark_reviewed':
            for report in reports:
                if report.status == Report.STATUS_PENDING:
                    report.mark_as_reviewed(request.user)
                    updated_count += 1
        
        elif action == 'mark_resolved':
            for report in reports:
                if report.status != Report.STATUS_RESOLVED:
                    report.mark_as_resolved(request.user)
                    updated_count += 1
        
        elif action == 'mark_rejected':
            for report in reports:
                if report.status != Report.STATUS_REJECTED:
                    report.mark_as_rejected(request.user)
                    updated_count += 1
        
        elif action == 'delete':
            reports.delete()
            return JsonResponse({
                'success': True,
                'message': f'{len(reports)} laporan berhasil dihapus'
            })

        else:
            return JsonResponse({
                'success': False,
                'message': 'Aksi tidak valid'
            }, status=400)

        return JsonResponse({
            'success': True,
            'message': f'{updated_count} laporan berhasil diperbarui'
        })


class UpdateReportStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    AJAX View untuk mengupdate status laporan individual.
    """
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')

        if new_status not in dict(Report.STATUS_CHOICES):
            return JsonResponse({
                'success': False,
                'message': 'Status tidak valid'
            }, status=400)

        # Update report
        report.status = new_status
        report.admin_notes = admin_notes
        
        if new_status == Report.STATUS_UNDER_REVIEW:
            report.mark_as_reviewed(request.user)
        elif new_status in [Report.STATUS_RESOLVED, Report.STATUS_REJECTED]:
            report.mark_as_resolved(request.user) if new_status == Report.STATUS_RESOLVED else report.mark_as_rejected(request.user)
        
        report.save()

        return JsonResponse({
            'success': True,
            'message': 'Status laporan berhasil diperbarui',
            'new_status': report.get_status_display(),
            'reviewed_by': report.reviewed_by.username if report.reviewed_by else '',
            'reviewed_at': report.reviewed_at.strftime('%d %b %Y %H:%M') if report.reviewed_at else ''
        })


class GetReportStatsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    AJAX View untuk mendapatkan statistik laporan.
    """
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request):
        today = timezone.now().date()
        
        # Basic stats
        stats = {
            'total': Report.objects.count(),
            'pending': Report.objects.filter(status=Report.STATUS_PENDING).count(),
            'under_review': Report.objects.filter(status=Report.STATUS_UNDER_REVIEW).count(),
            'resolved': Report.objects.filter(status=Report.STATUS_RESOLVED).count(),
            'rejected': Report.objects.filter(status=Report.STATUS_REJECTED).count(),
        }
        
        # Today's reports
        stats['today'] = Report.objects.filter(created_at__date=today).count()
        
        # By category
        stats['by_category'] = {
            category: Report.objects.filter(category=category).count()
            for category, _ in Report.CATEGORY_CHOICES
        }
        
        # By content type
        stats['by_content_type'] = {
            'post': Report.objects.filter(content_type__model='forumpost').count(),
            'comment': Report.objects.filter(content_type__model='comment').count(),
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })


class ReportSettingsView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View untuk mengatur pengaturan sistem pelaporan.
    """
    model = ReportSettings
    form_class = ReportSettingsForm
    template_name = 'report/report_settings.html'
    success_url = reverse_lazy('report:report-settings')

    def test_func(self):
        return self.request.user.is_staff

    def get_object(self):
        # Get or create settings object
        obj, created = ReportSettings.objects.get_or_create(pk=1)
        return obj

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)


class UserReportHistoryView(LoginRequiredMixin, ListView):
    """
    View untuk menampilkan riwayat laporan user.
    """
    model = Report
    template_name = 'report/user_report_history.html'
    context_object_name = 'reports'
    paginate_by = 10

    def get_queryset(self):
        return Report.objects.filter(
            reporter=self.request.user
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_reports'] = self.get_queryset().count()
        return context