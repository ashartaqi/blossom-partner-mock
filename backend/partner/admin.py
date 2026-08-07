from django.contrib import admin

from partner.models import PartnerUser


@admin.register(PartnerUser)
class PartnerUserAdmin(admin.ModelAdmin):
    list_display = ("email", "id", "first_name", "last_name", "created_at")
    search_fields = ("email",)
