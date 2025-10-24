from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import Report
from .forms import ReportUpdateForm

class StatusFilter(admin.SimpleListFilter):
    """Custom filter untuk status laporan"""
    title = 'Status Laporan'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('urgent', '🟡 Butuh Perhatian (Pending > 3 hari)'),
            ('pending', '⏳ Menunggu Review'),
            ('under_review', '🔍 Sedang Ditinjau'),
            ('resolved', '✅ Selesai'),
            ('dismissed', '❌ Ditolak'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'urgent':
            three_days_ago = timezone.now() - timedelta(days=3)
            return queryset.filter(
                status='pending',
                created_at__lte=three_days_ago
            )
        elif self.value() == 'pending':
            return queryset.filter(status='pending')
        elif self.value() == 'under_review':
            return queryset.filter(status='under_review')
        elif self.value() == 'resolved':
            return queryset.filter(status='resolved')
        elif self.value() == 'dismissed':
            return queryset.filter(status='dismissed')
        return queryset

class CategoryFilter(admin.SimpleListFilter):
    """Custom filter untuk kategori laporan"""
    title = 'Kategori Laporan'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return [
            ('sara', '🚫 SARA'),
            ('spam', '📢 Spam'),
            ('inappropriate', '🔞 Tidak Senonoh'),
            ('other', '❓ Lainnya'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category=self.value())
        return queryset

class DateRangeFilter(admin.SimpleListFilter):
    """Custom filter untuk rentang tanggal"""
    title = 'Rentang Tanggal'
    parameter_name = 'date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Hari Ini'),
            ('week', '7 Hari Terakhir'),
            ('month', '30 Hari Terakhir'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'today':
            today = timezone.now().date()
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif self.value() == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        return queryset

class ReportAdmin(admin.ModelAdmin):
    """Admin configuration for Report model"""
    
    # Konfigurasi tampilan list
    list_display = [
        'id',
        'content_type_display',
        'content_id',
        'category_display',
        'reporter_link',
        'status_display',
        'created_at_formatted',
        'handled_by_link',
        'handled_at_formatted',
        'quick_actions'
    ]
    
    list_filter = [
        StatusFilter,
        CategoryFilter,
        DateRangeFilter,
        'content_type',
        'created_at',
    ]
    
    search_fields = [
        'reporter__username',
        'reporter__email',
        'description',
        'content_id',
    ]
    
    list_per_page = 25
    list_max_show_all = 1000
    
    # Konfigurasi tampilan detail
    fieldsets = (
        ('Informasi Konten yang Dilaporkan', {
            'fields': (
                'content_type',
                'content_id',
                'get_content_preview',
            )
        }),
        ('Detail Laporan', {
            'fields': (
                'reporter',
                'category',
                'description',
                'created_at',
            )
        }),
        ('Penanganan Admin', {
            'fields': (
                'status',
                'handled_by',
                'handled_at',
                'admin_notes',
            )
        }),
    )
    
    readonly_fields = [
        'reporter',
        'content_type',
        'content_id',
        'created_at',
        'handled_at',
        'get_content_preview',
    ]
    
    # Custom actions
    actions = [
        'mark_as_under_review',
        'mark_as_resolved',
        'mark_as_dismissed',
        'bulk_delete',
    ]
    
    # Form customization
    form = ReportUpdateForm
    
    # Custom change list template dengan dashboard
    change_list_template = 'admin/report/report_change_list.html'
    
    def get_queryset(self, request):
        """Optimize queryset dengan select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('reporter', 'handled_by')
    
    # Custom methods untuk list_display
    def content_type_display(self, obj):
        """Display content type dengan icon"""
        icons = {
            'post': '📝',
            'comment': '💬',
        }
        icon = icons.get(obj.content_type, '📄')
        return format_html(
            '{} {}',
            icon,
            obj.get_content_type_display()
        )
    content_type_display.short_description = 'Jenis Konten'
    content_type_display.admin_order_field = 'content_type'
    
    def category_display(self, obj):
        """Display category dengan styling"""
        styles = {
            'sara': ('🚫', 'color: #c62828; font-weight: bold;'),
            'spam': ('📢', 'color: #ef6c00;'),
            'inappropriate': ('🔞', 'color: #7b1fa2; font-weight: bold;'),
            'other': ('❓', 'color: #303f9f;'),
        }
        icon, style = styles.get(obj.category, ('📄', ''))
        return format_html(
            '<span style="{}">{} {}</span>',
            style,
            icon,
            obj.get_category_display()
        )
    category_display.short_description = 'Kategori'
    category_display.admin_order_field = 'category'
    
    def status_display(self, obj):
        """Display status dengan badge styling"""
        styles = {
            'pending': ('⏳', 'background: #fff3cd; color: #856404; border: 1px solid #ffeaa7;'),
            'under_review': ('🔍', 'background: #cce7ff; color: #004085; border: 1px solid #b3d7ff;'),
            'resolved': ('✅', 'background: #d4edda; color: #155724; border: 1px solid #c3e6cb;'),
            'dismissed': ('❌', 'background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;'),
        }
        icon, style = styles.get(obj.status, ('📄', ''))
        return format_html(
            '<span style="{}; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">{} {}</span>',
            style,
            icon,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def reporter_link(self, obj):
        """Link ke admin user untuk reporter"""
        if obj.reporter:
            url = f"/admin/auth/user/{obj.reporter.id}/change/"
            return format_html(
                '<a href="{}" style="font-weight: 500;">{}</a>',
                url,
                obj.reporter.username
            )
        return "-"
    reporter_link.short_description = 'Pelapor'
    reporter_link.admin_order_field = 'reporter__username'
    
    def handled_by_link(self, obj):
        """Link ke admin user untuk handler"""
        if obj.handled_by:
            url = f"/admin/auth/user/{obj.handled_by.id}/change/"
            return format_html(
                '<a href="{}" style="font-weight: 500;">{}</a>',
                url,
                obj.handled_by.username
            )
        return "-"
    handled_by_link.short_description = 'Ditangani Oleh'
    handled_by_link.admin_order_field = 'handled_by__username'
    
    def created_at_formatted(self, obj):
        """Format tanggal created_at"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Dibuat'
    created_at_formatted.admin_order_field = 'created_at'
    
    def handled_at_formatted(self, obj):
        """Format tanggal handled_at"""
        if obj.handled_at:
            return obj.handled_at.strftime('%d/%m/%Y %H:%M')
        return "-"
    handled_at_formatted.short_description = 'Ditangani'
    handled_at_formatted.admin_order_field = 'handled_at'
    
    def quick_actions(self, obj):
        """Tombol aksi cepat"""
        buttons = []
        
        if obj.status == 'pending':
            buttons.append(
                f'<a href="/admin/report/report/{obj.id}/under-review/" class="button" style="background: #00a0d2; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-size: 12px;">Tinjau</a>'
            )
        
        if obj.status in ['pending', 'under_review']:
            buttons.append(
                f'<a href="/admin/report/report/{obj.id}/resolve/" class="button" style="background: #46b450; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-size: 12px; margin-left: 4px;">Selesai</a>'
            )
            buttons.append(
                f'<a href="/admin/report/report/{obj.id}/dismiss/" class="button" style="background: #dc3232; color: white; padding: 4px 8px; text-decoration: none; border-radius: 4px; font-size: 12px; margin-left: 4px;">Tolak</a>'
            )
        
        return format_html(' '.join(buttons)) if buttons else "-"
    quick_actions.short_description = 'Aksi Cepat'
    
    def get_content_preview(self, obj):
        """Preview konten yang dilaporkan (placeholder)"""
        # Di implementasi nyata, ini akan fetch konten aktual dari database
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; border-left: 4px solid #007cba;">'
            '<strong>Preview Konten:</strong><br>'
            'Ini adalah preview dari {} #{} yang dilaporkan. '
            'Di implementasi aktual, ini akan menampilkan konten sebenarnya.'
            '</div>',
            obj.get_content_type_display(),
            obj.content_id
        )
    get_content_preview.short_description = 'Preview Konten'
    
    # Custom actions methods
    def mark_as_under_review(self, request, queryset):
        """Action untuk menandai sebagai sedang ditinjau"""
        updated = queryset.update(
            status='under_review',
            handled_by=request.user,
            handled_at=timezone.now()
        )
        self.message_user(
            request, 
            f'{updated} laporan ditandai sebagai sedang ditinjau.'
        )
    mark_as_under_review.short_description = "🟡 Tandai sebagai sedang ditinjau"
    
    def mark_as_resolved(self, request, queryset):
        """Action untuk menandai sebagai selesai"""
        updated = queryset.update(
            status='resolved',
            handled_by=request.user,
            handled_at=timezone.now()
        )
        self.message_user(
            request, 
            f'{updated} laporan ditandai sebagai selesai.'
        )
    mark_as_resolved.short_description = "✅ Tandai sebagai selesai"
    
    def mark_as_dismissed(self, request, queryset):
        """Action untuk menandai sebagai ditolak"""
        updated = queryset.update(
            status='dismissed',
            handled_by=request.user,
            handled_at=timezone.now()
        )
        self.message_user(
            request, 
            f'{updated} laporan ditandai sebagai ditolak.'
        )
    mark_as_dismissed.short_description = "❌ Tandai sebagai ditolak"
    
    def bulk_delete(self, request, queryset):
        """Action untuk menghapus massal dengan konfirmasi"""
        if 'apply' in request.POST:
            count = queryset.count()
            queryset.delete()
            self.message_user(
                request,
                f'{count} laporan berhasil dihapus.'
            )
            return redirect(request.get_full_path())
        
        return render(
            request,
            'admin/report/bulk_delete_confirmation.html',
            context={
                'reports': queryset,
                'action': 'bulk_delete',
            }
        )
    bulk_delete.short_description = "🗑️ Hapus laporan terpilih"
    
    # Custom URLs untuk quick actions
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/under-review/',
                self.admin_site.admin_view(self.under_review_view),
                name='report_under_review',
            ),
            path(
                '<path:object_id>/resolve/',
                self.admin_site.admin_view(self.resolve_view),
                name='report_resolve',
            ),
            path(
                '<path:object_id>/dismiss/',
                self.admin_site.admin_view(self.dismiss_view),
                name='report_dismiss',
            ),
        ]
        return custom_urls + urls
    
    def under_review_view(self, request, object_id):
        """View untuk quick action under review"""
        report = self.get_object(request, object_id)
        if report:
            report.status = 'under_review'
            report.handled_by = request.user
            report.handled_at = timezone.now()
            report.save()
            self.message_user(request, f'Laporan #{report.id} ditandai sebagai sedang ditinjau.')
        return redirect('/admin/report/report/')
    
    def resolve_view(self, request, object_id):
        """View untuk quick action resolve"""
        report = self.get_object(request, object_id)
        if report:
            report.status = 'resolved'
            report.handled_by = request.user
            report.handled_at = timezone.now()
            report.save()
            self.message_user(request, f'Laporan #{report.id} ditandai sebagai selesai.')
        return redirect('/admin/report/report/')
    
    def dismiss_view(self, request, object_id):
        """View untuk quick action dismiss"""
        report = self.get_object(request, object_id)
        if report:
            report.status = 'dismissed'
            report.handled_by = request.user
            report.handled_at = timezone.now()
            report.save()
            self.message_user(request, f'Laporan #{report.id} ditandai sebagai ditolak.')
        return redirect('/admin/report/report/')
    
    # Custom methods untuk dashboard
    def changelist_view(self, request, extra_context=None):
        """Override changelist view untuk menambahkan stats"""
        # Stats untuk dashboard
        total_reports = Report.objects.count()
        pending_reports = Report.objects.filter(status='pending').count()
        under_review_reports = Report.objects.filter(status='under_review').count()
        urgent_reports = Report.objects.filter(
            status='pending',
            created_at__lte=timezone.now() - timedelta(days=3)
        ).count()
        
        # Stats by category
        category_stats = Report.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent activity
        recent_reports = Report.objects.select_related('reporter', 'handled_by').order_by('-created_at')[:10]
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_reports': total_reports,
            'pending_reports': pending_reports,
            'under_review_reports': under_review_reports,
            'urgent_reports': urgent_reports,
            'category_stats': category_stats,
            'recent_reports': recent_reports,
            'stats_data_json': json.dumps({
                'categories': [stat['category'] for stat in category_stats],
                'counts': [stat['count'] for stat in category_stats],
            })
        })
        
        return super().changelist_view(request, extra_context=extra_context)

# Register models
admin.site.register(Report, ReportAdmin)

# Custom admin site title
admin.site.site_header = "Moderasi Konten - Admin Dashboard"
admin.site.site_title = "Report System Admin"
admin.site.index_title = "Dashboard Moderasi"