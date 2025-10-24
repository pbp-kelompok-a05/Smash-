from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Ad

@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'ad_type', 'active', 'popup_delay_seconds', 'created_at')
    list_filter = ('ad_type', 'active')
    search_fields = ('title',)
