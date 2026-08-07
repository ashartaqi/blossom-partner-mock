"""Mounted at the site root.

The two ``/.well-known/`` paths are fixed by spec and have to sit directly under
the issuer origin, so this module is included with an empty prefix rather than
under an app path.
"""

from django.urls import path

from oidc import console, views

# The provider console. Staff-only, and namespaced away from the protocol paths
# above — these operate the provider, they are not part of it.
console_urlpatterns = [
    path("api/provider/overview/", console.ProviderOverview.as_view(), name="provider-overview"),
    path("api/provider/clients/", console.ClientList.as_view(), name="provider-clients"),
    path(
        "api/provider/clients/<str:client_id>/",
        console.ClientDetail.as_view(),
        name="provider-client",
    ),
    path(
        "api/provider/clients/<str:client_id>/rotate-secret/",
        console.ClientRotateSecret.as_view(),
        name="provider-client-rotate",
    ),
    path("api/provider/activity/", console.ProviderActivity.as_view(), name="provider-activity"),
]

urlpatterns = console_urlpatterns + [
    path(
        ".well-known/openid-configuration",
        views.openid_configuration,
        name="oidc-discovery",
    ),
    path(".well-known/jwks.json", views.jwks, name="oidc-jwks"),
    path("oauth/authorize", views.authorize, name="oidc-authorize"),
    path("oauth/token", views.token, name="oidc-token"),
    path("oauth/userinfo", views.userinfo, name="oidc-userinfo"),
    path("oauth/logout", views.logout_view, name="oidc-logout"),
    path("login/", views.login_page, name="login"),
]
