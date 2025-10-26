# report/urls.py
from django.urls import path
from . import views

app_name = 'report'

urlpatterns = [
    # =============================================
    # REPORT CRUD ENDPOINTS
    # =============================================
    
    # List reports (admin only) & Create new report
    path('', views.ReportAPIView.as_view(), name='report-list-create'),
    
    # Get, Update, Delete specific report (admin only)
    path('<int:report_id>/', views.ReportAPIView.as_view(), name='report-detail'),
    
    # =============================================
    # REPORT STATISTICS & DASHBOARD
    # =============================================
    
    # Report statistics (admin only)
    path('stats/', views.ReportStatsView.as_view(), name='report-stats'),
    
    # Dashboard overview (admin only)
    path('admin/dashboard/', views.ReportStatsView.as_view(), name='admin-dashboard'),
    
    # =============================================
    # REPORT FILTERING & SEARCH
    # =============================================
    
    # Filtered reports by status
    path('status/<str:status>/', 
         views.ReportAPIView.as_view(), 
         name='report-by-status'),
    
    # Filtered reports by category  
    path('category/<str:category>/', 
         views.ReportAPIView.as_view(), 
         name='report-by-category'),
    
    # Search reports
    path('search/', views.ReportAPIView.as_view(), name='report-search'),
    
    # =============================================
    # USER-SPECIFIC REPORT ENDPOINTS
    # =============================================
    
    # User's own reports
    path('user/reports/', views.ReportAPIView.as_view(), name='user-report-list'),
    
    # User's report statistics
    path('user/stats/', views.ReportStatsView.as_view(), name='user-report-stats'),
    
    # =============================================
    # BULK REPORT ACTIONS (Admin Only)
    # =============================================
    
    # Bulk update report status
    path('admin/bulk-update/', 
         views.ReportAPIView.as_view(), 
         name='admin-report-bulk-update'),
    
    # Bulk delete reports
    path('admin/bulk-delete/', 
         views.ReportAPIView.as_view(), 
         name='admin-report-bulk-delete'),

    path('api/reports/', views.ReportAPIView.as_view(), name='report-api'),
    path('api/reports/<int:report_id>/', views.ReportAPIView.as_view(), name='report-detail'),
    path('api/reports/stats/', views.ReportStatsView.as_view(), name='report-stats'),
]