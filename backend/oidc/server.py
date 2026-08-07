"""Authlib wiring — the whole protocol, in one file.

Everything that could be got subtly wrong (parsing the authorization request,
validating redirect_uri, comparing the PKCE verifier, encoding and signing the ID
token, formatting error responses to spec) belongs to Authlib. What is left here
is the handful of questions only Blossom can answer: which client is this, where
do I store a code, who is the member, and what may this client learn about them.

That split is the point. Every line below is about Blossom's own data. There is no
place in this file where a mistake becomes a cryptographic mistake.
"""

import logging
from datetime import timedelta

from authlib.integrations.django_oauth2 import (
    AuthorizationServer,
    BearerTokenValidator,
    ResourceProtector,
)
from authlib.oauth2.rfc6749 import InvalidRequestError, grants
from authlib.oauth2.rfc7636 import CodeChallenge
from authlib.oidc.core import UserInfo
from authlib.oidc.core.grants import OpenIDCode
from django.conf import settings
from django.utils import timezone

from oidc import keys
from oidc.models import OAuth2AuthorizationCode, OAuth2Client, OAuth2Token

audit = logging.getLogger("sso.audit")


def issuer() -> str:
    """The ``iss`` claim, and the base of every advertised endpoint.

    One value, used everywhere, because a relying party pins it: they fetch
    discovery from this URL and then refuse any token whose ``iss`` is not exactly
    it. A mismatch between what we advertise and what we sign is an outage.
    """
    return settings.OIDC["ISSUER"].rstrip("/")


def user_claims(user, scope: str) -> UserInfo:
    """Everything Blossom is willing to disclose, filtered by the granted scope.

    Standard OIDC claim names throughout — ``sub``, ``email``, ``given_name``,
    ``picture``. Standard names are the reason a relying party needs no
    Blossom-specific code to read this.

    ``sub`` is the contract. It must be stable for a given human forever and never
    be reused for a different one, because Surmount stores it and matches on it to
    decide whose brokerage account to open. A UUID primary key gives both for free;
    an email address gives neither, since emails get changed and recycled.
    """
    claims = {"sub": str(user.id)}

    if "profile" in scope:
        claims.update(
            {
                "name": f"{user.first_name} {user.last_name}".strip(),
                "given_name": user.first_name,
                "family_name": user.last_name,
                "picture": user.picture,
                "updated_at": int(user.created_at.timestamp()),
            }
        )

    if "email" in scope:
        claims.update(
            {
                "email": user.email,
                # Blossom verified this at signup. Saying so lets Surmount skip its
                # own verification mail; saying so falsely would let anyone who can
                # set an email address here take over an account there.
                "email_verified": True,
            }
        )

    return UserInfo(**claims)


class BlossomOpenIDCode(OpenIDCode):
    """Turns the authorization code into a signed ID token."""

    def __init__(self):
        # nonce is required, not optional. It is the relying party's replay defence,
        # and a provider that quietly accepts requests without one lets a sloppy
        # integration ship without ever noticing it has no protection.
        super().__init__(require_nonce=True)

    def exists_nonce(self, nonce, request):
        return OAuth2AuthorizationCode.objects.filter(
            client_id=request.payload.client_id, nonce=nonce
        ).exists()

    def resolve_client_private_key(self, client):
        return keys.private_key_set()

    def get_client_algorithm(self, client):
        return client.id_token_signed_response_alg or "RS256"

    def get_encode_header(self, client):
        # kid tells the relying party which published key to verify against, so we
        # can rotate signing keys without coordinating a downtime window.
        return {"alg": self.get_client_algorithm(client), "kid": keys.key_id()}

    def get_client_claims(self, client):
        return {"iss": issuer(), "aud": [client.get_client_id()]}

    def generate_user_info(self, user, scope):
        return user_claims(user, scope)


class RequiredCodeChallenge(CodeChallenge):
    """PKCE for everyone, not just public clients.

    Authlib's ``required=True`` only forces a verifier when the client
    authenticated as public, and its challenge check returns quietly when the
    authorization request simply omits ``code_challenge``. A confidential client
    could therefore skip PKCE entirely and still get a code — a silent downgrade
    to the weaker flow, which is exactly what RFC 9700 tells providers to stop
    accepting.

    Refusing at the authorization endpoint means a relying party that forgets
    PKCE finds out on their first test run rather than never.
    """

    def validate_code_challenge(self, grant, redirect_uri):
        challenge = grant.request.payload.data.get("code_challenge")
        if not challenge:
            raise InvalidRequestError(
                "Missing 'code_challenge'. PKCE is required.",
                redirect_uri=redirect_uri,
            )

        method = grant.request.payload.data.get("code_challenge_method")
        if method != "S256":
            # "plain" is not a challenge — it is the verifier in clear text, so a
            # code interceptor gets the verifier along with it.
            raise InvalidRequestError(
                "Only S256 is supported for 'code_challenge_method'.",
                redirect_uri=redirect_uri,
            )

        return super().validate_code_challenge(grant, redirect_uri)


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Where authorization codes live between the two halves of the hand-off."""

    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post"]

    def save_authorization_code(self, code, request):
        payload = request.payload
        auth_time = getattr(request, "blossom_auth_time", None)

        return OAuth2AuthorizationCode.objects.create(
            code=code,
            client_id=request.client.client_id,
            user=request.user,
            redirect_uri=payload.redirect_uri or "",
            response_type=payload.response_type or "",
            scope=payload.scope or "",
            nonce=payload.data.get("nonce", "") or "",
            code_challenge=payload.data.get("code_challenge", "") or "",
            code_challenge_method=payload.data.get("code_challenge_method", "") or "",
            auth_time=auth_time or int(timezone.now().timestamp()),
            expires_at=timezone.now()
            + timedelta(seconds=settings.OIDC["CODE_TTL_SECONDS"]),
        )

    def query_authorization_code(self, code, client):
        row = OAuth2AuthorizationCode.objects.filter(
            code=code, client_id=client.client_id
        ).first()
        if row and not row.is_expired():
            return row
        if row:
            audit.warning("token REJECTED expired-code client=%s", client.client_id)
        return None

    def delete_authorization_code(self, authorization_code):
        # Deleted on redemption, not marked used: a code is single-use, and the row
        # has no value afterwards. Authlib calls this inside the same request that
        # issues the token, so a replay finds nothing.
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        user = authorization_code.user
        # Between minting the code and redeeming it, the member may have been
        # suspended. The token would outlive that, so check now rather than trust
        # the snapshot.
        return user if user.is_active else None


server = AuthorizationServer(OAuth2Client, OAuth2Token)
server.register_grant(
    AuthorizationCodeGrant,
    [BlossomOpenIDCode(), RequiredCodeChallenge(required=True)],
)

# No refresh-token grant, on purpose. The access token issued here does one thing —
# read /userinfo, once, immediately — so a refresh token would extend the lifetime
# of a credential that has no long-lived job. Surmount runs its own session after
# the hand-off; it never needs to come back and ask Blossom again.

require_oauth = ResourceProtector()
require_oauth.register_token_validator(BearerTokenValidator(OAuth2Token))
