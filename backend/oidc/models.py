"""Storage for the OpenID Provider.

Three tables, which is all OAuth 2.0 authorization-code needs:

    OAuth2Client              who is allowed to ask, and where they may be sent back
    OAuth2AuthorizationCode   a 60-second single-use receipt for one completed login
    OAuth2Token               the access token that reads /userinfo

Each implements the mixin Authlib expects, so Authlib drives the protocol and this
file only answers questions about our own data. Nothing here parses a request or
builds a response — that is deliberate, and it is why there is no hand-rolled
crypto anywhere in this app.
"""

import hashlib
import hmac
import secrets
import time

from authlib.oauth2.rfc6749 import ClientMixin, TokenMixin
from authlib.oidc.core import AuthorizationCodeMixin
from django.conf import settings
from django.db import models


def _split(value):
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def now_ts() -> int:
    # Module level rather than a lambda so makemigrations can serialise it.
    return int(time.time())


class OAuth2Client(models.Model, ClientMixin):
    """A relying party. Surmount is one; there would be one row per integration.

    The secret is stored as a SHA-256 digest, never in the clear. A database dump
    then contains nothing an attacker can present at the token endpoint, and the
    only copy of the real value lives in the relying party's own configuration.
    That is also why registration prints the secret exactly once.
    """

    client_id = models.CharField(max_length=64, unique=True, db_index=True)
    client_secret_hash = models.CharField(max_length=64)
    client_name = models.CharField(max_length=120)

    # Newline-separated exact URLs. Exact, because prefix or wildcard matching on
    # redirect_uri is the single most reliably exploited bug in OAuth deployments:
    # anything looser lets an attacker append their own host and receive the code.
    redirect_uris = models.TextField(
        help_text="One absolute URL per line. Matched exactly — no wildcards, no prefixes."
    )
    post_logout_redirect_uris = models.TextField(blank=True, default="")

    scope = models.CharField(max_length=255, default="openid profile email")
    grant_types = models.TextField(default="authorization_code\nrefresh_token")
    response_types = models.TextField(default="code")
    token_endpoint_auth_method = models.CharField(
        max_length=64, default="client_secret_basic"
    )
    id_token_signed_response_alg = models.CharField(max_length=16, default="RS256")

    # First-party integrations skip the consent screen. Blossom's members are being
    # handed to Blossom's own investing product, so asking them to authorise the
    # bank to talk to the bank is noise. A third-party client would leave this off
    # and see the consent page.
    is_trusted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OAuth2 client"

    def __str__(self):
        return f"{self.client_name} ({self.client_id})"

    def set_secret(self, raw: str):
        self.client_secret_hash = hash_secret(raw)

    # --- ClientMixin -------------------------------------------------------

    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        uris = _split(self.redirect_uris)
        return uris[0] if uris else None

    def get_allowed_scope(self, scope):
        if not scope:
            return ""
        allowed = set(self.scope.split())
        return " ".join(s for s in scope.split() if s in allowed)

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in _split(self.redirect_uris)

    def check_client_secret(self, client_secret):
        # Constant-time. A plain == on a secret leaks it a byte at a time to anyone
        # who can measure response latency, and this endpoint is the one door
        # between a code and a member's identity.
        return hmac.compare_digest(
            self.client_secret_hash, hash_secret(client_secret or "")
        )

    def check_endpoint_auth_method(self, method, endpoint):
        if endpoint == "token":
            return self.token_endpoint_auth_method == method
        return True

    def check_response_type(self, response_type):
        return response_type in _split(self.response_types)

    def check_grant_type(self, grant_type):
        return grant_type in _split(self.grant_types)


class OAuth2AuthorizationCode(models.Model, AuthorizationCodeMixin):
    """One completed login, redeemable once, for sixty seconds.

    This is the only artefact of the hand-off that travels through the member's
    browser, and it is worth nothing on its own: redeeming it also requires the
    client secret and the PKCE verifier, neither of which the browser ever sees.
    """

    code = models.CharField(max_length=120, unique=True, db_index=True)
    client_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oidc_codes"
    )

    redirect_uri = models.TextField(default="")
    response_type = models.TextField(default="")
    scope = models.TextField(default="")

    # Echoed back inside the ID token. The relying party generated it, so seeing it
    # come back proves this token answers *their* request and is not one captured
    # from an earlier session and replayed.
    nonce = models.CharField(max_length=255, blank=True, default="")

    # PKCE. The relying party keeps the verifier and sends only its hash here; a
    # stolen code cannot be redeemed without the verifier, which never left them.
    code_challenge = models.CharField(max_length=255, blank=True, default="")
    code_challenge_method = models.CharField(max_length=16, blank=True, default="")

    # When the member actually authenticated, not when the code was minted. A
    # relying party that cares about session freshness reads this from the token.
    auth_time = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = "OAuth2 authorization code"

    def __str__(self):
        return f"code={self.code[:8]}… client={self.client_id} user={self.user_id}"

    def is_expired(self):
        from django.utils import timezone

        return timezone.now() >= self.expires_at

    # --- AuthorizationCodeMixin -------------------------------------------

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return self.scope

    def get_nonce(self):
        return self.nonce or None

    def get_auth_time(self):
        return self.auth_time or None

    def get_acr(self):
        return None

    def get_amr(self):
        return None


class OAuth2Token(models.Model, TokenMixin):
    """The access token, whose only privilege here is reading /userinfo.

    Deliberately narrow. It is not a session on Blossom and it cannot move money —
    the worst a leaked one can do is disclose the profile of the member who was
    already being handed over.
    """

    client_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="oidc_tokens"
    )

    token_type = models.CharField(max_length=40, default="Bearer")
    access_token = models.CharField(max_length=255, unique=True, db_index=True)
    refresh_token = models.CharField(max_length=255, blank=True, default="", db_index=True)
    scope = models.TextField(default="")

    issued_at = models.IntegerField(default=now_ts)
    expires_in = models.IntegerField(default=0)
    revoked_at = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "OAuth2 token"

    def __str__(self):
        return f"token={self.access_token[:8]}… client={self.client_id} user={self.user_id}"

    # --- TokenMixin --------------------------------------------------------

    def check_client(self, client):
        return hmac.compare_digest(self.client_id, client.get_client_id())

    def get_scope(self):
        return self.scope

    def get_expires_in(self):
        return self.expires_in

    def is_expired(self):
        return self.issued_at + self.expires_in < time.time()

    def is_revoked(self):
        return self.revoked_at is not None

    def get_user(self):
        return self.user

    def get_client(self):
        return OAuth2Client.objects.filter(client_id=self.client_id).first()


def generate_client_secret() -> str:
    """256 bits from the OS CSPRNG. Printed once at registration, then only hashed."""
    return secrets.token_urlsafe(32)
