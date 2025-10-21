from datetime import timezone
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'reporter', 
        'get_reported_content_type',
        'reason', 
        'status', 
        'created_at',
        'resolved_by'
    ]
    
    list_filter = [
        'status', 
        'reason', 
        'created_at',
        'resolved_at'
    ]
    
    search_fields = [
        'reporter__username',
        'reporter__email',
        'description',
        'admin_notes'
    ]
    
    readonly_fields = [
        'reporter',
        'content_type',
        'object_id',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Informasi Pelapor', {
            'fields': ('reporter', 'created_at', 'updated_at')
        }),
        ('Konten yang Dilaporkan', {
            'fields': ('content_type', 'object_id')
        }),
        ('Detail Laporan', {
            'fields': ('reason', 'description')
        }),
        ('Moderasi', {
            'fields': ('status', 'resolved_by', 'resolved_at', 'admin_notes')
        }),
    )
    
    actions = ['mark_as_resolved', 'mark_as_pending']
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            status=Report.STATUS_RESOLVED,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} laporan ditandai sebagai selesai.')
    
    mark_as_resolved.short_description = "Tandai laporan terpilih sebagai selesai"
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status=Report.STATUS_PENDING)
        self.message_user(request, f'{updated} laporan ditandai sebagai pending.')
    
    mark_as_pending.short_description = "Tandai laporan terpilih sebagai pending"