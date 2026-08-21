"""The provider console API.

What an identity provider gives the people integrating with it: register a
relying party, see and edit its registration, rotate its secret, and watch the
authorizations actually flowing through. Auth0's dashboard, Okta's admin, Google
Cloud's OAuth consent screen — this is the same small set of operations, over the
same three tables.

Deliberately separate from ``partner/`` — these endpoints operate the *provider*,
not the member-facing platform, and they are gated differently for that reason.

Access
------
Staff only. Everything here is administrative: registering a client mints a
credential that can ask for members' identities, and editing a redirect URI is
the single most security-critical field in an OAuth deployment. Ordinary members
sign in through the same app, so ``IsAuthenticated`` would hand every one of them
the provider's controls.
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from oidc.models import (
    OAuth2AuthorizationCode,
    OAuth2Client,
    OAuth2Token,
    generate_client_secret,
)


def _lines(value):
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _client_json(client, secret=None):
    """One client, as the console shows it.

    ``secret`` is present exactly once — in the response that created or rotated
    it. It is never stored in the clear, so no later request can return it.
    """
    data = {
        "client_id": client.client_id,
        "client_name": client.client_name,
        "redirect_uris": _lines(client.redirect_uris),
        "post_logout_redirect_uris": _lines(client.post_logout_redirect_uris),
        "scope": client.scope,
        "grant_types": _lines(client.grant_types),
        "response_types": _lines(client.response_types),
        "token_endpoint_auth_method": client.token_endpoint_auth_method,
        "id_token_signed_response_alg": client.id_token_signed_response_alg,
        "is_trusted": client.is_trusted,
        "created_at": client.created_at,
    }
    if secret is not None:
        data["client_secret"] = secret
    data["relying_party_env"] = _relying_party_env(client, secret)
    return data


def _relying_party_env(client, secret=None):
    """The four values the integrating side has to configure, ready to paste.

    Every one of them is exact-match checked somewhere: the issuer against the
    ``iss`` claim, the redirect URI against this registration, the client id and
    secret at the token endpoint. Transcribing them by eye is how an integration
    spends a morning on a typo, so the console hands them over verbatim.
    """
    prefix = f"SSO_{settings.PARTNER_SLUG.upper().replace('-', '_')}"
    redirect = _lines(client.redirect_uris)
    lines = [
        f"{prefix}_OIDC_ISSUER={settings.PUBLIC_BASE_URL}",
        f"{prefix}_OIDC_CLIENT_ID={client.client_id}",
        # Only ever real in the response that minted it. Anywhere else this is a
        # reminder of which variable it belongs in, not a recoverable value.
        f"{prefix}_OIDC_CLIENT_SECRET={secret or '<shown once, when created or rotated>'}",
        f"{prefix}_OIDC_REDIRECT_URI={redirect[0] if redirect else '<no redirect URI registered>'}",
    ]
    return "\n".join(lines)


class ProviderOverview(APIView):
    """Everything a client is configured *from*, plus how busy the provider is."""

    permission_classes = (IsAdminUser,)

    def get(self, request):
        base = settings.PUBLIC_BASE_URL
        now = timezone.now()

        # The issuer is configuration, not something derived per request, because
        # it is the `iss` claim and relying parties demand an exact match. That
        # makes it easy to serve this through a tunnel and hand out URLs pointing
        # at localhost, which fail on the other side for reasons the error does
        # not explain. Report the origin the browser actually used so the console
        # can say so out loud.
        request_origin = f"{request.scheme}://{request.get_host()}"

        codes = OAuth2AuthorizationCode.objects.all()
        return Response(
            {
                "issuer": base,
                "request_origin": request_origin,
                "issuer_matches_request": request_origin == base,
                "endpoints": {
                    "discovery": f"{base}/.well-known/openid-configuration",
                    "jwks": f"{base}/.well-known/jwks.json",
                    "authorize": f"{base}/oauth/authorize",
                    "token": f"{base}/oauth/token",
                    "userinfo": f"{base}/oauth/userinfo",
                    "end_session": f"{base}/oauth/logout",
                },
                "stats": {
                    "clients": OAuth2Client.objects.count(),
                    "codes_issued": codes.count(),
                    # A code still unexpired and unredeemed. Should hover near zero:
                    # they live sixty seconds and are spent almost immediately.
                    "codes_live": codes.filter(expires_at__gt=now).count(),
                    "tokens_issued": OAuth2Token.objects.count(),
                    "tokens_active": OAuth2Token.objects.filter(
                        revoked_at__isnull=True
                    ).count(),
                },
            }
        )


class ClientList(APIView):
    """GET  — every registered relying party.
    POST — register a new one. The secret comes back once, and never again."""

    permission_classes = (IsAdminUser,)

    def get(self, request):
        # Authorization counts per client, so the list shows which integrations
        # are actually live rather than merely configured.
        counts = {
            row["client_id"]: row["n"]
            for row in OAuth2AuthorizationCode.objects.values("client_id").annotate(
                n=Count("id")
            )
        }
        clients = []
        for client in OAuth2Client.objects.order_by("client_name"):
            data = _client_json(client)
            data["authorizations"] = counts.get(client.client_id, 0)
            clients.append(data)
        return Response(clients)

    def post(self, request):
        client_id = (request.data.get("client_id") or "").strip()
        redirect_uris = request.data.get("redirect_uris") or []

        if not client_id:
            return Response(
                {"error": "client_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if OAuth2Client.objects.filter(client_id=client_id).exists():
            return Response(
                {"error": f"{client_id} is already registered."},
                status=status.HTTP_409_CONFLICT,
            )
        # A client with no redirect URI cannot complete a single authorization, and
        # an empty list is the shape that tempts someone to "allow any" later.
        if not redirect_uris:
            return Response(
                {"error": "At least one redirect_uri is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invalid = [u for u in redirect_uris if not str(u).startswith(("http://", "https://"))]
        if invalid:
            return Response(
                {"error": f"redirect_uri must be an absolute URL: {invalid[0]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret = generate_client_secret()
        client = OAuth2Client(
            client_id=client_id,
            client_name=(request.data.get("client_name") or client_id).strip(),
            redirect_uris="\n".join(str(u).strip() for u in redirect_uris),
            post_logout_redirect_uris="\n".join(
                str(u).strip() for u in (request.data.get("post_logout_redirect_uris") or [])
            ),
            scope=(request.data.get("scope") or "openid profile email").strip(),
            is_trusted=bool(request.data.get("is_trusted")),
            # No refresh-token grant — see the note in oidc/server.py.
            grant_types="authorization_code",
            response_types="code",
        )
        client.set_secret(secret)
        client.save()

        return Response(
            _client_json(client, secret=secret), status=status.HTTP_201_CREATED
        )


class ClientDetail(APIView):
    """Read, edit or remove one relying party."""

    permission_classes = (IsAdminUser,)

    def _get(self, client_id):
        return OAuth2Client.objects.filter(client_id=client_id).first()

    def get(self, request, client_id):
        client = self._get(client_id)
        if not client:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_client_json(client))

    def patch(self, request, client_id):
        client = self._get(client_id)
        if not client:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if "client_name" in request.data:
            client.client_name = (request.data["client_name"] or "").strip() or client.client_id

        if "redirect_uris" in request.data:
            uris = [str(u).strip() for u in (request.data["redirect_uris"] or []) if str(u).strip()]
            if not uris:
                return Response(
                    {"error": "At least one redirect_uri is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            invalid = [u for u in uris if not u.startswith(("http://", "https://"))]
            if invalid:
                return Response(
                    {"error": f"redirect_uri must be an absolute URL: {invalid[0]}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            client.redirect_uris = "\n".join(uris)

        if "post_logout_redirect_uris" in request.data:
            client.post_logout_redirect_uris = "\n".join(
                str(u).strip()
                for u in (request.data["post_logout_redirect_uris"] or [])
                if str(u).strip()
            )

        if "scope" in request.data:
            client.scope = (request.data["scope"] or "").strip() or "openid"

        if "is_trusted" in request.data:
            client.is_trusted = bool(request.data["is_trusted"])

        client.save()
        return Response(_client_json(client))

    def delete(self, request, client_id):
        """Remove the registration and everything it issued.

        ``client_id`` on codes and tokens is a plain column, not a foreign key, so
        nothing cascades on its own: deleting a client would otherwise leave its
        activity behind, attributed to a client that no longer exists. Worse, a
        client registered again under the same id would inherit it.
        """
        client = self._get(client_id)
        if not client:
            return Response(status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            codes, _ = OAuth2AuthorizationCode.objects.filter(
                client_id=client_id
            ).delete()
            tokens, _ = OAuth2Token.objects.filter(client_id=client_id).delete()
            client.delete()

        return Response({"client_id": client_id, "codes": codes, "tokens": tokens})


class ClientRotateSecret(APIView):
    """Issue a new secret. The old one stops working the moment this returns.

    There is no grace period and no second live secret, which is the honest
    behaviour for a mock: a real provider would offer overlapping secrets so a
    client can roll without downtime, and pretending to do that here would teach
    the wrong thing about what this provider actually supports.
    """

    permission_classes = (IsAdminUser,)

    def post(self, request, client_id):
        client = OAuth2Client.objects.filter(client_id=client_id).first()
        if not client:
            return Response(status=status.HTTP_404_NOT_FOUND)

        secret = generate_client_secret()
        client.set_secret(secret)
        client.save(update_fields=["client_secret_hash"])
        return Response(_client_json(client, secret=secret))


class ProviderActivity(APIView):
    """The last authorizations to pass through, newest first.

    This is the view that turns a broken integration into an obvious one: a code
    issued with no token behind it means the client never reached /oauth/token,
    which is nearly always a wrong secret or a redirect_uri that did not match.
    """

    permission_classes = (IsAdminUser,)
    LIMIT = 25

    def get(self, request):
        now = timezone.now()
        # One lookup for both tables. A row whose client has since been deleted
        # keeps its id and reads as gone, rather than silently blank.
        names = dict(OAuth2Client.objects.values_list("client_id", "client_name"))

        def named(client_id):
            return {
                "client_id": client_id,
                "client_name": names.get(client_id) or "",
                "client_exists": client_id in names,
            }

        codes = (
            OAuth2AuthorizationCode.objects.select_related("user")
            .order_by("-created_at")[: self.LIMIT]
        )
        tokens = (
            OAuth2Token.objects.select_related("user").order_by("-issued_at")[: self.LIMIT]
        )

        return Response(
            {
                "codes": [
                    {
                        "code_preview": f"{c.code[:8]}…",
                        **named(c.client_id),
                        "user": c.user.email,
                        "scope": c.scope,
                        "redirect_uri": c.redirect_uri,
                        "used_pkce": bool(c.code_challenge),
                        "created_at": c.created_at,
                        "expired": c.expires_at <= now,
                    }
                    for c in codes
                ],
                "tokens": [
                    {
                        "token_preview": f"{t.access_token[:8]}…",
                        **named(t.client_id),
                        "user": t.user.email,
                        "scope": t.scope,
                        "issued_at": t.issued_at,
                        "expires_in": t.expires_in,
                        "revoked": t.revoked_at is not None,
                    }
                    for t in tokens
                ],
            }
        )
