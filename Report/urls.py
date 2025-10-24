from django.urls import path
from . import views

app_name = 'report'

urlpatterns = [
    # User URLs
    path('create/', views.ReportCreateView.as_view(), name='report-create'),
    path('my-reports/', views.UserReportHistoryView.as_view(), name='user-report-history'),
    
    # Admin URLs
    path('admin/', views.ReportListView.as_view(), name='report-list'),
    path('admin/<uuid:pk>/', views.ReportDetailView.as_view(), name='report-detail'),
    path('admin/<uuid:pk>/update/', views.ReportUpdateView.as_view(), name='report-update'),
    path('admin/<uuid:pk>/delete/', views.ReportDeleteView.as_view(), name='report-delete'),
    path('admin/settings/', views.ReportSettingsView.as_view(), name='report-settings'),
    
    # AJAX URLs
    path('admin/bulk-action/', views.BulkReportActionView.as_view(), name='bulk-report-action'),
    path('admin/<uuid:pk>/update-status/', views.UpdateReportStatusView.as_view(), name='update-report-status'),
    path('admin/stats/', views.GetReportStatsView.as_view(), name='report-stats'),
]