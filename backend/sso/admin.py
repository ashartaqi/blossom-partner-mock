from django.contrib import admin

from sso.models import SSOCode


@admin.register(SSOCode)
class SSOCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "created_at", "expires_at", "used_at")
    readonly_fields = ("code", "user", "claims", "redirect_uri", "created_at", "expires_at", "used_at")
