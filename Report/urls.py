from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # ==================== REPORT CRUD URLS ====================
    path('', views.report_list, name='report_list'),
    path('create/', views.create_report, name='create_report'),
    path('create/<int:content_type_id>/<uuid:object_id>/', views.create_report, name='create_report_for_content'),
    path('<uuid:pk>/', views.report_detail, name='report_detail'),
    path('<uuid:pk>/edit/', views.update_report, name='update_report'),
    path('<uuid:pk>/delete/', views.delete_report, name='delete_report'),
    
    # ==================== REPORT ADMIN ACTIONS URLS ====================
    path('admin/', views.admin_report_list, name='admin_report_list'),
    path('<uuid:pk>/mark-reviewed/', views.mark_report_reviewed, name='mark_report_reviewed'),
    path('<uuid:pk>/resolve/', views.resolve_report, name='resolve_report'),
    path('<uuid:pk>/reject/', views.reject_report, name='reject_report'),
    path('<uuid:pk>/reopen/', views.reopen_report, name='reopen_report'),
    
    # ==================== REPORT SETTINGS URLS ====================
    path('settings/', views.report_settings, name='report_settings'),
    
    # ==================== API URLS (JSON/XML) ====================
    path('api/json/', views.show_json, name='show_json'),
    path('api/xml/', views.show_xml, name='show_xml'),
    path('api/json/<uuid:pk>/', views.show_json_by_id, name='show_json_by_id'),
    path('api/xml/<uuid:pk>/', views.show_xml_by_id, name='show_xml_by_id'),
]
