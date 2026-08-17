from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Blossom's own API, used by the Blossom web app.
    path("api/auth/", include("partner.urls")),
    # The member's own banking data — accounts, balances, transactions.
    path("api/banking/", include("banking.urls")),
    # The OpenID Provider. Included with no prefix because /.well-known/ paths are
    # fixed by spec and must sit directly under the issuer origin.
    path("", include("oidc.urls")),
]
