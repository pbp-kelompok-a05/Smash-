from django.urls import path
from authentication.views import login, register, logout, change_password, delete_account

app_name = 'authentication'

urlpatterns = [
    path('login/', login, name='login'),
    path('register/', register, name='register'),
    path('logout/', logout, name='logout'),
    path('change_password/', change_password, name='change_password'),
    path('delete_account/', delete_account, name='delete_account'),
]