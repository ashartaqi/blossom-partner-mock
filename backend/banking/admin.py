from django.contrib import admin

from banking.models import Account, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "member", "kind", "number_last4", "balance", "is_primary")
    list_filter = ("kind", "is_primary")
    search_fields = ("member__email", "number_last4")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "account", "amount", "category", "status", "posted_at")
    list_filter = ("category", "status")
    search_fields = ("description", "account__member__email")
