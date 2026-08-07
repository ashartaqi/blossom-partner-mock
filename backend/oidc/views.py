"""The five endpoints that make Blossom an OpenID Provider.

    GET  /.well-known/openid-configuration   what this provider supports
    GET  /.well-known/jwks.json              the public half of the signing key
    GET  /oauth/authorize                    front channel — the member's browser
    POST /oauth/token                        back channel — Surmount's server
    GET  /oauth/userinfo                     back channel — profile, Bearer-guarded

Two of these are on the front channel and three on the back. Which side an endpoint
sits on decides what it is allowed to trust: the front channel is a browser under
the member's control and can be tampered with, so nothing it carries is believed
without a back-channel check. Identity only ever moves on the back channel.
"""

import logging

from authlib.oauth2 import OAuth2Error
from django.conf import settings
from django.contrib.auth import login as session_login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from oidc import keys
from oidc.server import issuer, require_oauth, server, user_claims

audit = logging.getLogger("sso.audit")

# Set at login, read when minting a code, published as the ID token's auth_time.
AUTH_TIME_SESSION_KEY = "blossom_auth_time"


def mark_authenticated(request, user):
    """Start a Blossom browser session for ``user``.

    Called from the SPA's login endpoint as well as from the login page below, so
    both routes leave the browser in the same state. ``/oauth/authorize`` works off
    this session cookie and nothing else — a token in the SPA's localStorage is
    invisible to a top-level navigation, which is exactly what an authorize request
    is.
    """
    if not hasattr(user, "backend"):
        # Set by authenticate(), absent when we sign someone in straight after
        # signup. login() needs to record which backend vouched for the user so
        # the next request can load them back.
        user.backend = settings.AUTHENTICATION_BACKENDS[0]
    session_login(request, user)
    request.session[AUTH_TIME_SESSION_KEY] = int(timezone.now().timestamp())


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


@require_http_methods(["GET"])
@cache_control(max_age=300, public=True)
def openid_configuration(request):
    """The document that makes integration self-configuring.

    A relying party is given one value — the issuer URL — and reads everything else
    from here. That is why endpoint URLs are not part of the integration brief: they
    are discovered, so we can move them without breaking anyone.
    """
    base = issuer()
    return JsonResponse(
        {
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "userinfo_endpoint": f"{base}/oauth/userinfo",
            "jwks_uri": f"{base}/.well-known/jwks.json",
            "end_session_endpoint": f"{base}/oauth/logout",
            "scopes_supported": ["openid", "profile", "email"],
            "response_types_supported": ["code"],
            "response_modes_supported": ["query"],
            "grant_types_supported": ["authorization_code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": [
                "client_secret_basic",
                "client_secret_post",
            ],
            # Advertising only S256 tells a client not to bother with "plain",
            # which is not a challenge at all — it is the verifier in clear text.
            "code_challenge_methods_supported": ["S256"],
            "claims_supported": [
                "sub",
                "iss",
                "aud",
                "exp",
                "iat",
                "auth_time",
                "nonce",
                "name",
                "given_name",
                "family_name",
                "picture",
                "email",
                "email_verified",
                "updated_at",
            ],
        }
    )


@require_http_methods(["GET"])
@cache_control(max_age=300, public=True)
def jwks(request):
    """Public keys. Cacheable, but briefly — a client that caches this forever
    cannot follow a key rotation, and one that never caches it hammers us on every
    verification."""
    return JsonResponse(keys.public_jwks())


# ---------------------------------------------------------------------------
# Front channel
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def authorize(request):
    """Where the member's browser arrives, and leaves with a code.

    ``@login_required`` is the entire "already signed in?" test. If the member has a
    Blossom session, this is invisible to them: two redirects and they are in the
    investing app. If they do not, they see Blossom's own login page — never
    Surmount's, which is the property that makes this SSO rather than a second
    account.
    """
    try:
        grant = server.get_consent_grant(request, end_user=request.user)
    except OAuth2Error as error:
        audit.warning("authorize REJECTED %s: %s", error.error, error.description)
        if error.redirect_uri:
            # The redirect_uri was recognised, so the client is real and the fault
            # is in the rest of the request. Reporting it back to them is how they
            # find out; the member never sees it.
            return server.handle_error_response(request, error)
        # No verified redirect_uri — an unknown client, or one naming a URI nobody
        # registered. Redirecting here is precisely how an attacker would use this
        # endpoint as a relay, so the error stops on our own page instead.
        return _error_page(request, error)

    client = grant.client

    if not client.is_trusted:
        if request.method == "GET":
            return render(
                request,
                "oidc/consent.html",
                {"client": client, "scopes": (grant.request.payload.scope or "").split()},
            )
        if request.POST.get("consent") != "allow":
            audit.info("authorize DENIED by user client=%s", client.client_id)
            return server.create_authorization_response(
                request=grant.request, grant_user=None, grant=grant
            )

    # Carried into the ID token as auth_time, so a relying party that needs a fresh
    # login can tell how old this session is.
    grant.request.blossom_auth_time = request.session.get(AUTH_TIME_SESSION_KEY)

    audit.info(
        "authorize OK client=%s sub=%s scope=%s",
        client.client_id,
        request.user.id,
        grant.request.payload.scope,
    )
    return server.create_authorization_response(
        request=grant.request, grant_user=request.user, grant=grant
    )


def _error_page(request, error):
    """Only the error code reaches the page.

    Authlib's description quotes the offending parameter back — including the
    redirect_uri, which is attacker-controlled on exactly the request that lands
    here. Django would escape it, so this is not XSS, but a page that mirrors
    whatever a stranger puts in a URL is a page worth using in a phishing chain.
    The description goes to the audit log, where the developer who needs it is.
    """
    return render(
        request, "oidc/error.html", {"code": error.error}, status=error.status_code
    )


# ---------------------------------------------------------------------------
# Back channel
# ---------------------------------------------------------------------------


@csrf_exempt
@require_http_methods(["POST"])
def token(request):
    """Server-to-server. Trades the code for tokens, and burns the code.

    CSRF-exempt because there is no browser session to forge: the caller proves
    itself with a client secret in the Authorization header. Django's CSRF
    machinery protects cookie-authenticated requests, and would only ever reject
    legitimate traffic here.

    Three independent things must line up for this to succeed — the code, the
    client secret, and the PKCE verifier. Stealing any one of them is not enough.
    """
    response = server.create_token_response(request)
    if response.status_code != 200:
        audit.warning("token REJECTED status=%s body=%s", response.status_code, response.content[:200])
    return response


@require_http_methods(["GET"])
@require_oauth("openid")
def userinfo(request):
    """The member's profile, for the holder of a valid access token.

    Scoped: a token granted only ``openid`` gets a ``sub`` and nothing else. The
    claims a client receives are decided here, from what was actually granted —
    never from what the client asks for at this endpoint.
    """
    token_row = request.oauth_token
    return JsonResponse(dict(user_claims(token_row.user, token_row.get_scope())))


# ---------------------------------------------------------------------------
# Login page — Blossom's own, the one place a member's password is ever typed
# ---------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def login_page(request):
    """Server-rendered because ``/oauth/authorize`` is a top-level navigation.

    The SPA at :5300 signs in over XHR and would do just as well for its own pages,
    but a browser arriving here from Surmount has no SPA loaded. A provider needs a
    login surface that works from a cold navigation.
    """
    from django.contrib.auth import authenticate

    next_url = request.GET.get("next") or request.POST.get("next") or "/"
    # Only ever continue to somewhere on this host. Without this check the login
    # page is an open redirect, and a phishing link could bounce a freshly
    # authenticated member to an attacker's page.
    if not next_url.startswith("/"):
        next_url = "/"

    error = None
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("email", ""),
            password=request.POST.get("password", ""),
        )
        if user and user.is_active:
            mark_authenticated(request, user)
            return redirect(next_url)
        # One message for both causes. Saying "no such account" tells an attacker
        # which addresses are worth guessing passwords for.
        error = "Email or password is incorrect."

    return render(
        request,
        "oidc/login.html",
        {"next": next_url, "error": error, "spa_url": settings.OIDC["SPA_URL"]},
    )


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """RP-initiated logout: ends the Blossom session, then returns the browser.

    ``post_logout_redirect_uri`` is checked against the client's registered list for
    the same reason ``redirect_uri`` is — an unchecked one turns the logout endpoint
    into an open redirect that carries Blossom's name.
    """
    from django.contrib.auth import logout as session_logout

    from oidc.models import OAuth2Client

    requested = request.GET.get("post_logout_redirect_uri")
    client_id = request.GET.get("client_id")

    target = settings.OIDC["SPA_URL"]
    if requested and client_id:
        client = OAuth2Client.objects.filter(client_id=client_id).first()
        allowed = [
            line.strip()
            for line in (client.post_logout_redirect_uris if client else "").splitlines()
            if line.strip()
        ]
        if requested in allowed:
            target = requested
        else:
            audit.warning(
                "logout REJECTED redirect client=%s uri=%s", client_id, requested
            )

    session_logout(request)
    return redirect(target)
