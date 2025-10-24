from django.urls import path
from . import views  # Impor views.py dari folder 'main'

urlpatterns = [
    # Ini akan mencocokkan URL root (path kosong) 
    # yang diarahkan dari project utama
    path('', views.main_page_view, name='main-page'),
]