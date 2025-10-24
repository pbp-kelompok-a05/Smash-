from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Advertisement

@admin.register(Advertisement)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'ad_type', 'is_active', 'delay', 'created_at')
    list_filter = ('ad_type', 'is_active')
    search_fields = ('title',)
