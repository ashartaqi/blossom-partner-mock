import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from sso.services import SSOError, mint_code, redeem_code, verify_client_credentials

audit = logging.getLogger("sso.audit")


class SSOInitiateView(APIView):
    """POST /sso/initiate  —  called by FE1 when the user clicks "Investments".

    Authenticated as the logged-in partner user. Mints a one-time code and returns
    the URL the browser should be sent to.

    Response: { "redirect_url": "http://localhost:4001/sso/callback?code=..." }
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            _, redirect_url = mint_code(request.user, request.data.get("redirect_uri"))
        except SSOError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"redirect_url": redirect_url})


class SSOExchangeView(APIView):
    """POST /sso/exchange  —  back-channel, called by Surmount (BE2). Never by a browser.

    This is the one place a user's identity leaves the platform, so it is guarded by
    a client secret rather than a user session, and it burns the code on the way out.

    Request:  { "code", "client_id", "client_secret" }
    Response: { "external_user_id", "email", "first_name", "last_name" }
    """

    permission_classes = (AllowAny,)
    throttle_classes = (AnonRateThrottle,)
    authentication_classes = ()  # client-credential auth, not user auth

    def post(self, request):
        client_id = request.data.get("client_id")
        client_secret = request.data.get("client_secret")

        if not verify_client_credentials(client_id, client_secret):
            audit.warning("exchange REJECTED bad-credentials client_id=%r", client_id)
            return Response({"error": "Invalid client credentials."},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            claims = redeem_code(request.data.get("code"))
        except SSOError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(claims)
