from django.contrib import admin
from .models import Advertisement

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    """Read-only view agar tetap sesuai rubric"""
    list_display = ("title", "ad_type", "is_active", "created_at", "owner")
    list_filter = ("ad_type", "is_active", "created_at")
    search_fields = ("title", "description")

    readonly_fields = (
        "title", "description", "image", "link",
        "ad_type", "popup_delay_seconds", "is_active",
        "created_at", "owner",
    )

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
