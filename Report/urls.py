from django.urls import path
from . import views

app_name = 'report'

urlpatterns = [
    # =========================================================================
    # AJAX ENDPOINTS
    # =========================================================================
    
    # POST /reports/create/
    # Membuat laporan baru via AJAX
    # Data: content_type, content_id, category, description
    path('create/', views.create_report, name='create_report'),
    
    # POST /reports/<report_id>/update-status/
    # Update status laporan oleh admin via AJAX
    # Data: status
    path('<int:report_id>/update-status/', views.update_report_status, name='update_report_status'),
    
    # DELETE /reports/<report_id>/delete/
    # Menghapus laporan via AJAX
    path('<int:report_id>/delete/', views.delete_report, name='delete_report'),
    
    # =========================================================================
    # ADMIN VIEWS (Requires admin/staff permission)
    # =========================================================================
    
    # GET /reports/
    # Daftar semua laporan dengan filtering dan pagination
    # Query Params: ?status=<status>&category=<category>&page=<page>
    path('', views.report_list, name='report_list'),
    
    # GET /reports/dashboard/
    # Dashboard statistik laporan untuk admin
    path('dashboard/', views.report_dashboard, name='report_dashboard'),
    
    # GET /reports/<report_id>/
    # Detail laporan individual
    path('<int:report_id>/', views.report_detail, name='report_detail'),
    
    # =========================================================================
    # USER VIEWS (Requires login)
    # =========================================================================
    
    # GET /reports/my-reports/
    # Daftar laporan yang dibuat oleh user yang login
    # Query Params: ?page=<page>
    path('my-reports/', views.my_reports, name='my_reports'),
]