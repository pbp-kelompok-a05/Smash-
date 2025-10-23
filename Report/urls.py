from django.urls import path
from . import views

urlpatterns = [
    path("", views.report_list, name="report_list"),
    path("create/", views.create_report, name="create_report"),
    path("<int:report_id>/", views.report_detail, name="report_detail"),
    # API URLs
    path("api/json/", views.show_json, name="show_json"),
    path("api/xml/", views.show_xml, name="show_xml"),
    path("api/json/<int:report_id>/", views.show_json_by_id, name="show_json_by_id"),
    path("api/xml/<int:report_id>/", views.show_xml_by_id, name="show_xml_by_id"),
]
