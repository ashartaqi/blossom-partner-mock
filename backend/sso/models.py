from django.conf import settings
from django.db import models
from django.utils import timezone


class SSOCode(models.Model):
    """A one-time hand-off code.

    This is the ONLY thing that ever touches the browser. It is opaque, lives for
    60 seconds, and can be redeemed exactly once. The user's actual identity travels
    separately, server-to-server, over the /sso/exchange back-channel.

    ``claims`` is snapshotted at mint time rather than resolved at exchange time, so
    a redemption reflects who the user was when they clicked — not who they might
    have been edited into during the 60-second window.
    """

    code = models.CharField(max_length=128, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sso_codes")
    claims = models.JSONField()
    redirect_uri = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["expires_at", "used_at"])]

    def __str__(self):
        return f"SSOCode({self.code[:8]}… user={self.user_id} used={bool(self.used_at)})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None
