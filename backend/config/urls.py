from pathlib import Path

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

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

# The built SPA, when there is one. Its routes are client-side, so anything not
# claimed above returns index.html and lets the router decide — otherwise a
# reload on /dashboard is a 404. Listed last, and never shadowing a real route.
_SPA_INDEX = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "index.html"
if _SPA_INDEX.exists():
    urlpatterns += [
        re_path(
            r"^(?!api/|oauth/|admin/|static/|login/|logout/|\.well-known/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="spa",
        )
    ]
