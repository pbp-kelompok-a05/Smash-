# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('reports/create/', views.create_report, name='create_report'),
    path('reports/', views.report_list, name='report_list'),
    path('reports/my/', views.my_reports, name='my_reports'),
    path('reports/dashboard/', views.report_dashboard, name='report_dashboard'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/<int:report_id>/update-status/', views.update_report_status, name='update_report_status'),
    path('reports/<int:report_id>/delete/', views.delete_report, name='delete_report'),
]