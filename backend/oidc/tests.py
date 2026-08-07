"""What the provider must refuse.

Blossom is the side holding everyone's identity, so the interesting cases are all
the ones where it declines: a redirect_uri nobody registered, a code redeemed
twice, a PKCE verifier that does not match, a client presenting the wrong secret.

Run with:  manage.py test oidc
"""

import base64
import time
from urllib.parse import parse_qs, urlparse

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from joserfc import jwt as joserfc_jwt
from joserfc.jwk import KeySet

from authlib.oauth2.rfc7636 import create_s256_code_challenge
from oidc.models import OAuth2AuthorizationCode, OAuth2Client, OAuth2Token
from partner.models import PartnerUser

CLIENT_ID = "test-rp"
CLIENT_SECRET = "test-rp-secret"
REDIRECT_URI = "https://rp.test/callback/"
VERIFIER = "a" * 64  # PKCE allows 43-128 unreserved characters


def basic_auth(client_id, secret):
    raw = f"{client_id}:{secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


class ProviderTestCase(TestCase):
    def setUp(self):
        self.user = PartnerUser.objects.create_user(
            email="jenna@blossom.test",
            password="correct horse battery staple",
            first_name="Jenna",
            last_name="Rivera",
        )
        self.client_row = OAuth2Client(
            client_id=CLIENT_ID,
            client_name="Test RP",
            redirect_uris=REDIRECT_URI,
            post_logout_redirect_uris="https://rp.test/goodbye",
            scope="openid profile email",
            grant_types="authorization_code",
            response_types="code",
            is_trusted=True,
        )
        self.client_row.set_secret(CLIENT_SECRET)
        self.client_row.save()

    # -- helpers ------------------------------------------------------------

    def authorize_params(self, **overrides):
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": "openid profile email",
            "state": "state-123",
            "nonce": "nonce-123",
            "code_challenge": create_s256_code_challenge(VERIFIER),
            "code_challenge_method": "S256",
        }
        params.update(overrides)
        return {k: v for k, v in params.items() if v is not None}

    def sign_in(self):
        self.client.force_login(self.user)

    def get_code(self, **overrides):
        self.sign_in()
        response = self.client.get(reverse("oidc-authorize"), self.authorize_params(**overrides))
        query = parse_qs(urlparse(response["Location"]).query)
        return query["code"][0]

    def redeem(self, code, verifier=VERIFIER, secret=CLIENT_SECRET):
        return self.client.post(
            reverse("oidc-token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            HTTP_AUTHORIZATION=basic_auth(CLIENT_ID, secret),
        )


class DiscoveryTests(ProviderTestCase):
    def test_discovery_describes_this_provider(self):
        body = self.client.get(reverse("oidc-discovery")).json()

        self.assertEqual(body["issuer"], "http://localhost:9000")
        self.assertTrue(body["authorization_endpoint"].endswith("/oauth/authorize"))
        self.assertTrue(body["jwks_uri"].endswith("/.well-known/jwks.json"))
        self.assertEqual(body["response_types_supported"], ["code"])
        self.assertEqual(body["id_token_signing_alg_values_supported"], ["RS256"])
        # Only S256. "plain" is not a challenge — it is the verifier in clear text.
        self.assertEqual(body["code_challenge_methods_supported"], ["S256"])

    def test_jwks_publishes_only_public_material(self):
        body = self.client.get(reverse("oidc-jwks")).json()
        key = body["keys"][0]

        self.assertEqual(key["kty"], "RSA")
        self.assertEqual(key["use"], "sig")
        self.assertTrue(key["kid"])
        self.assertIn("n", key)
        self.assertIn("e", key)
        # The private exponent and primes. Publishing any of these would hand
        # over the ability to mint an identity for every member on the platform.
        for private in ("d", "p", "q", "dp", "dq", "qi"):
            self.assertNotIn(private, key)


class AuthorizeTests(ProviderTestCase):
    def test_a_signed_in_member_is_bounced_straight_back_with_a_code(self):
        self.sign_in()
        response = self.client.get(reverse("oidc-authorize"), self.authorize_params())

        self.assertEqual(response.status_code, 302)
        location = urlparse(response["Location"])
        self.assertEqual(f"{location.scheme}://{location.netloc}{location.path}", REDIRECT_URI)

        query = parse_qs(location.query)
        self.assertTrue(query["code"][0])
        # state must be echoed exactly, or the relying party cannot tie this
        # response to the request it made.
        self.assertEqual(query["state"], ["state-123"])

    def test_an_anonymous_visitor_sees_blossoms_own_login(self):
        """Never Surmount's. A member typing their Blossom password into anything
        but Blossom is the failure mode SSO exists to prevent."""
        response = self.client.get(reverse("oidc-authorize"), self.authorize_params())

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/"))
        # The original request is preserved, so signing in continues the hand-off
        # rather than dumping them on a dashboard.
        self.assertIn("next=", response["Location"])

    def test_an_unregistered_redirect_uri_is_never_redirected_to(self):
        """The single most exploited bug in OAuth deployments. Redirecting the
        error would make this endpoint a relay to whatever host the caller named."""
        self.sign_in()
        response = self.client.get(
            reverse("oidc-authorize"),
            self.authorize_params(redirect_uri="https://evil.test/steal"),
        )

        self.assertNotEqual(response.status_code, 302)
        self.assertNotIn("evil.test", response.content.decode())
        self.assertEqual(OAuth2AuthorizationCode.objects.count(), 0)

    def test_a_prefix_of_a_registered_uri_is_not_a_match(self):
        self.sign_in()
        response = self.client.get(
            reverse("oidc-authorize"),
            self.authorize_params(redirect_uri=REDIRECT_URI + "../evil"),
        )
        self.assertNotEqual(response.status_code, 302)

    def test_an_unknown_client_is_refused(self):
        self.sign_in()
        response = self.client.get(
            reverse("oidc-authorize"), self.authorize_params(client_id="who-are-you")
        )
        self.assertNotEqual(response.status_code, 302)

    def test_a_request_without_a_nonce_is_refused(self):
        """The relying party's replay defence. A provider that quietly accepts
        requests without one lets a sloppy integration ship with no protection."""
        self.sign_in()
        response = self.client.get(reverse("oidc-authorize"), self.authorize_params(nonce=None))

        query = parse_qs(urlparse(response["Location"]).query)
        self.assertIn("error", query)
        self.assertNotIn("code", query)

    def test_a_request_without_pkce_is_refused(self):
        self.sign_in()
        response = self.client.get(
            reverse("oidc-authorize"),
            self.authorize_params(code_challenge=None, code_challenge_method=None),
        )
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertIn("error", query)

    def test_the_code_records_what_the_token_endpoint_will_need(self):
        code = self.get_code()
        row = OAuth2AuthorizationCode.objects.get(code=code)

        self.assertEqual(row.user_id, self.user.id)
        self.assertEqual(row.nonce, "nonce-123")
        self.assertEqual(row.code_challenge, create_s256_code_challenge(VERIFIER))
        self.assertEqual(row.code_challenge_method, "S256")
        # Sixty seconds. RFC 6749 caps this at ten minutes and recommends shorter.
        self.assertLessEqual((row.expires_at - row.created_at).total_seconds(), 60)


class ConsentTests(ProviderTestCase):
    def test_a_third_party_client_has_to_ask(self):
        self.client_row.is_trusted = False
        self.client_row.save()
        self.sign_in()

        response = self.client.get(reverse("oidc-authorize"), self.authorize_params())

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test RP", response.content)
        self.assertEqual(OAuth2AuthorizationCode.objects.count(), 0)

    def test_denying_consent_issues_no_code(self):
        self.client_row.is_trusted = False
        self.client_row.save()
        self.sign_in()

        params = self.authorize_params()
        response = self.client.post(
            reverse("oidc-authorize") + "?" + _urlencode(params), {"consent": "deny"}
        )

        self.assertEqual(OAuth2AuthorizationCode.objects.count(), 0)
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(query["error"], ["access_denied"])

    def test_allowing_consent_issues_a_code(self):
        self.client_row.is_trusted = False
        self.client_row.save()
        self.sign_in()

        params = self.authorize_params()
        response = self.client.post(
            reverse("oidc-authorize") + "?" + _urlencode(params), {"consent": "allow"}
        )

        query = parse_qs(urlparse(response["Location"]).query)
        self.assertTrue(query["code"][0])


class TokenTests(ProviderTestCase):
    def test_a_valid_redemption_returns_a_verifiable_id_token(self):
        code = self.get_code()
        response = self.redeem(code)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["token_type"], "Bearer")
        # No refresh token: this access token reads /userinfo once and is done.
        self.assertNotIn("refresh_token", body)

        jwks = self.client.get(reverse("oidc-jwks")).json()
        token = joserfc_jwt.decode(body["id_token"], KeySet.import_key_set(jwks))

        self.assertEqual(token.claims["iss"], "http://localhost:9000")
        self.assertEqual(token.claims["sub"], str(self.user.id))
        self.assertEqual(token.claims["aud"], [CLIENT_ID])
        self.assertEqual(token.claims["nonce"], "nonce-123")
        self.assertEqual(token.claims["email"], "jenna@blossom.test")
        self.assertGreater(token.claims["exp"], int(time.time()))
        # kid names which published key to verify against, so rotation needs no
        # coordinated downtime.
        self.assertTrue(token.header["kid"])
        self.assertEqual(token.header["alg"], "RS256")

    def test_a_code_works_exactly_once(self):
        code = self.get_code()
        self.assertEqual(self.redeem(code).status_code, 200)
        self.assertEqual(self.redeem(code).status_code, 400)

    def test_a_wrong_pkce_verifier_is_refused(self):
        """The whole point of PKCE: an attacker who intercepts the code still
        cannot redeem it, because the verifier never left the relying party."""
        code = self.get_code()
        response = self.redeem(code, verifier="b" * 64)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_grant")

    def test_a_missing_pkce_verifier_is_refused(self):
        code = self.get_code()
        response = self.client.post(
            reverse("oidc-token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            HTTP_AUTHORIZATION=basic_auth(CLIENT_ID, CLIENT_SECRET),
        )
        self.assertEqual(response.status_code, 400)

    def test_a_wrong_client_secret_is_refused(self):
        code = self.get_code()
        response = self.redeem(code, secret="not-the-secret")

        self.assertEqual(response.status_code, 401)
        # And the code survives, because it was never redeemed.
        self.assertTrue(OAuth2AuthorizationCode.objects.filter(code=code).exists())

    def test_an_expired_code_is_refused(self):
        code = self.get_code()
        row = OAuth2AuthorizationCode.objects.get(code=code)
        row.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        row.save(update_fields=["expires_at"])

        self.assertEqual(self.redeem(code).status_code, 400)

    def test_a_mismatched_redirect_uri_is_refused(self):
        """The code is bound to the URI it was issued for. Without this check a
        code obtained for one registered URI could be redeemed against another."""
        code = self.get_code()
        response = self.client.post(
            reverse("oidc-token"),
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://rp.test/somewhere-else/",
                "code_verifier": VERIFIER,
            },
            HTTP_AUTHORIZATION=basic_auth(CLIENT_ID, CLIENT_SECRET),
        )
        self.assertEqual(response.status_code, 400)

    def test_a_member_suspended_between_the_two_legs_gets_no_token(self):
        """The code was minted while they were active; the token would outlive
        that. Checked at redemption rather than trusted from the snapshot."""
        code = self.get_code()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        self.assertEqual(self.redeem(code).status_code, 400)


class UserInfoTests(ProviderTestCase):
    def _access_token(self, scope="openid profile email"):
        code = self.get_code(scope=scope)
        return self.redeem(code).json()["access_token"]

    def test_a_valid_token_reads_the_profile(self):
        token = self._access_token()
        body = self.client.get(
            reverse("oidc-userinfo"), HTTP_AUTHORIZATION=f"Bearer {token}"
        ).json()

        self.assertEqual(body["sub"], str(self.user.id))
        self.assertEqual(body["email"], "jenna@blossom.test")
        self.assertEqual(body["given_name"], "Jenna")

    def test_claims_are_limited_to_the_granted_scope(self):
        """A client that asked only for openid learns that this is a Blossom
        account and nothing else — not what it sends to this endpoint, but what
        the member actually granted."""
        token = self._access_token(scope="openid")
        body = self.client.get(
            reverse("oidc-userinfo"), HTTP_AUTHORIZATION=f"Bearer {token}"
        ).json()

        self.assertEqual(body["sub"], str(self.user.id))
        self.assertNotIn("email", body)
        self.assertNotIn("given_name", body)

    def test_no_token_is_refused(self):
        self.assertEqual(self.client.get(reverse("oidc-userinfo")).status_code, 401)

    def test_a_made_up_token_is_refused(self):
        response = self.client.get(
            reverse("oidc-userinfo"), HTTP_AUTHORIZATION="Bearer not-a-real-token"
        )
        self.assertEqual(response.status_code, 401)

    def test_an_expired_token_is_refused(self):
        token = self._access_token()
        row = OAuth2Token.objects.get(access_token=token)
        row.issued_at = int(time.time()) - 10_000
        row.expires_in = 60
        row.save(update_fields=["issued_at", "expires_in"])

        response = self.client.get(
            reverse("oidc-userinfo"), HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 401)


class LogoutTests(ProviderTestCase):
    def test_logout_ends_the_session(self):
        self.sign_in()
        self.client.get(reverse("oidc-logout"))

        # With the session gone, an authorize request has to ask for a password
        # again — which is what makes signing out mean something.
        response = self.client.get(reverse("oidc-authorize"), self.authorize_params())
        self.assertTrue(response["Location"].startswith("/login/"))

    def test_an_unregistered_post_logout_uri_is_ignored(self):
        self.sign_in()
        response = self.client.get(
            reverse("oidc-logout"),
            {"client_id": CLIENT_ID, "post_logout_redirect_uri": "https://evil.test/"},
        )
        self.assertNotIn("evil.test", response["Location"])

    def test_a_registered_post_logout_uri_is_honoured(self):
        self.sign_in()
        response = self.client.get(
            reverse("oidc-logout"),
            {"client_id": CLIENT_ID, "post_logout_redirect_uri": "https://rp.test/goodbye"},
        )
        self.assertEqual(response["Location"], "https://rp.test/goodbye")


class LoginPageTests(ProviderTestCase):
    def test_correct_credentials_continue_the_hand_off(self):
        response = self.client.post(
            reverse("login"),
            {
                "email": "jenna@blossom.test",
                "password": "correct horse battery staple",
                "next": "/oauth/authorize?client_id=x",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/oauth/authorize?client_id=x")

    def test_wrong_credentials_say_nothing_specific(self):
        """One message for both causes. "No such account" tells an attacker which
        addresses are worth guessing passwords for."""
        response = self.client.post(
            reverse("login"), {"email": "jenna@blossom.test", "password": "wrong"}
        )
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Email or password is incorrect", body)

        missing = self.client.post(
            reverse("login"), {"email": "nobody@blossom.test", "password": "wrong"}
        )
        self.assertIn("Email or password is incorrect", missing.content.decode())

    def test_an_offsite_next_is_dropped(self):
        """Otherwise the login page is an open redirect, and a phishing link could
        bounce a freshly authenticated member onto an attacker's page."""
        response = self.client.post(
            reverse("login"),
            {
                "email": "jenna@blossom.test",
                "password": "correct horse battery staple",
                "next": "https://evil.test/",
            },
        )
        self.assertEqual(response["Location"], "/")


class ClientSecretTests(ProviderTestCase):
    def test_the_secret_is_only_ever_stored_hashed(self):
        """A database dump then contains nothing that can be presented at the
        token endpoint."""
        row = OAuth2Client.objects.get(client_id=CLIENT_ID)

        self.assertNotIn(CLIENT_SECRET, row.client_secret_hash)
        self.assertEqual(len(row.client_secret_hash), 64)  # SHA-256, hex
        self.assertTrue(row.check_client_secret(CLIENT_SECRET))
        self.assertFalse(row.check_client_secret("close-but-no"))
        self.assertFalse(row.check_client_secret(""))
        self.assertFalse(row.check_client_secret(None))


def _urlencode(params):
    from urllib.parse import urlencode

    return urlencode(params)
