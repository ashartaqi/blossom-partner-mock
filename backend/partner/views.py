from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from banking.seed import open_accounts
from oidc.views import mark_authenticated
from partner.serializers import LoginSerializer, PartnerUserSerializer, SignupSerializer


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def _sign_in(request, user):
    """Issue both credentials this platform uses.

    A bearer token for the web app's own XHR calls, and a session cookie for
    everything that arrives as a browser navigation — which is what an OIDC
    authorize request is. Without the cookie, a member who is plainly signed in to
    Blossom would be asked to sign in again the moment they tapped Investments.
    """
    mark_authenticated(request._request, user)
    return {**_tokens_for(user), "user": PartnerUserSerializer(user).data}


class SignupView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Open their accounts before the first response, so the app never renders
        # a member with no balance, no history and nothing to fund an investment
        # from. Idempotent, so a retried signup cannot double their money.
        open_accounts(user)

        return Response(_sign_in(request, user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(_sign_in(request, serializer.validated_data["user"]))


class MeView(APIView):
    """Protected. FE1's RequireAuth wrapper calls this to prove the token works."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(PartnerUserSerializer(request.user).data)


class IntegrationView(APIView):
    """Feeds the Developer page: the registration Surmount was actually given.

    Read from the database rather than from a document someone typed, so it
    cannot drift from what the provider will really accept. If a redirect URI
    shown here is wrong, the hand-off is broken *now* — this is a view of the
    running configuration, not a description of it.

    The client secret is absent, and could not be shown even if we wanted to:
    only its SHA-256 digest is stored. It is printed once at registration, and
    after that the only copy lives in Surmount's own configuration.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from django.conf import settings

        from oidc.models import OAuth2Client
        from oidc.server import user_claims

        def lines(value):
            return [line.strip() for line in (value or "").splitlines() if line.strip()]

        base = settings.PUBLIC_BASE_URL
        clients = [
            {
                "client_id": c.client_id,
                "client_name": c.client_name,
                "redirect_uris": lines(c.redirect_uris),
                "post_logout_redirect_uris": lines(c.post_logout_redirect_uris),
                "scope": c.scope,
                "grant_types": lines(c.grant_types),
                "response_types": lines(c.response_types),
                "token_endpoint_auth_method": c.token_endpoint_auth_method,
                "id_token_signed_response_alg": c.id_token_signed_response_alg,
                "skips_consent": c.is_trusted,
            }
            for c in OAuth2Client.objects.all()
        ]

        return Response(
            {
                "issuer": base,
                "discovery_url": f"{base}/.well-known/openid-configuration",
                "jwks_url": f"{base}/.well-known/jwks.json",
                "clients": clients,
                # Produced by the same function the token and userinfo
                # endpoints call, at the scope this client is granted — so the
                # page cannot advertise one set of claims while the hand-off
                # sends another. It previously showed the *token-exchange*
                # shape (external_user_id/first_name), which OIDC never sends.
                "claims_for_you": dict(
                    user_claims(request.user, clients[0]["scope"] if clients else "openid")
                ),
            }
        )
