from django.contrib import admin

from oidc.models import OAuth2AuthorizationCode, OAuth2Client, OAuth2Token


@admin.register(OAuth2Client)
class OAuth2ClientAdmin(admin.ModelAdmin):
    list_display = ("client_name", "client_id", "is_trusted", "created_at")
    search_fields = ("client_name", "client_id")
    # The hash is shown, never an input. Rotating a secret goes through
    # `manage.py register_oidc_client --rotate-secret`, which prints the new value
    # once; there is no path here that could leave a secret in an admin log.
    readonly_fields = ("client_secret_hash", "created_at")


@admin.register(OAuth2AuthorizationCode)
class OAuth2AuthorizationCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "client_id", "user", "created_at", "expires_at")
    readonly_fields = tuple(f.name for f in OAuth2AuthorizationCode._meta.fields)


@admin.register(OAuth2Token)
class OAuth2TokenAdmin(admin.ModelAdmin):
    list_display = ("access_token", "client_id", "user", "scope", "issued_at")
    readonly_fields = tuple(f.name for f in OAuth2Token._meta.fields)
