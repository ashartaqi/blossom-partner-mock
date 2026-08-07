"""The two operations that make up the hand-off. Keep this file boring and correct."""

import hmac
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

from sso.models import SSOCode

audit = logging.getLogger("sso.audit")


class SSOError(Exception):
    """Raised for any rejected hand-off. The message is safe to return to a caller."""


def _config():
    return settings.SSO


def verify_client_credentials(client_id, client_secret):
    """Authenticate BE2 on the back-channel.

    Both comparisons are constant-time. A plain ``==`` on the secret would leak it
    one byte at a time to anyone who can measure response latency, and this endpoint
    is the single door to every user's identity on the platform.
    """
    cfg = _config()
    ok_id = hmac.compare_digest(str(client_id or ""), cfg["CLIENT_ID"])
    ok_secret = hmac.compare_digest(str(client_secret or ""), cfg["CLIENT_SECRET"])
    # Evaluate both before returning so the timing does not reveal which one failed.
    return ok_id and ok_secret


def resolve_redirect_uri(requested):
    """Exact-match allow-list.

    Without this, /sso/initiate is an open redirect that hands a valid identity code
    to whatever host the caller names.
    """
    cfg = _config()
    if not requested:
        return cfg["DEFAULT_REDIRECT_URI"]
    if requested not in cfg["ALLOWED_REDIRECT_URIS"]:
        raise SSOError("redirect_uri is not allow-listed.")
    return requested


def mint_code(user, requested_redirect_uri=None):
    """Create a one-time code for ``user`` and return (code, redirect_url).

    Shared by both entry points into the hand-off, so the two can never drift apart
    in what they issue.
    """
    cfg = _config()
    redirect_uri = resolve_redirect_uri(requested_redirect_uri)

    # 32 bytes of CSPRNG entropy -> 256 bits, per the security requirements.
    code = secrets.token_urlsafe(32)
    sso_code = SSOCode.objects.create(
        code=code,
        user=user,
        claims=user.sso_claims(),
        redirect_uri=redirect_uri,
        expires_at=timezone.now() + timedelta(seconds=cfg["CODE_TTL_SECONDS"]),
    )

    audit.info(
        "mint code=%s… user=%s redirect=%s ttl=%ss",
        code[:8], user.external_user_id, redirect_uri, cfg["CODE_TTL_SECONDS"],
    )
    redirect_url = f"{redirect_uri}?{urlencode({'code': code})}"
    return sso_code, redirect_url


def redeem_code(code):
    """Burn ``code`` and return its claims. Raises SSOError on any problem.

    The burn is a single conditional UPDATE rather than read-check-write, so two
    concurrent redemptions of the same code cannot both succeed: exactly one of them
    matches ``used_at IS NULL`` and updates a row.
    """
    if not code:
        raise SSOError("Missing code.")

    now = timezone.now()
    burned = SSOCode.objects.filter(
        code=code, used_at__isnull=True, expires_at__gt=now
    ).update(used_at=now)

    if burned != 1:
        # Distinguish the cases for the audit log only — the caller gets one
        # generic message, so a probe cannot tell "expired" from "never existed".
        existing = SSOCode.objects.filter(code=code).first()
        if existing is None:
            reason = "unknown"
        elif existing.is_used:
            reason = "already-used"
        else:
            reason = "expired"
        audit.warning("redeem REJECTED code=%s… reason=%s", str(code)[:8], reason)
        raise SSOError("Invalid or expired code.")

    sso_code = SSOCode.objects.get(code=code)
    audit.info("redeem OK code=%s… user=%s", str(code)[:8], sso_code.claims.get("external_user_id"))
    return sso_code.claims
