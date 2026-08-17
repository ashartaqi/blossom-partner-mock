import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from partner.avatars import new_avatar_url


class PartnerUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        # Drawn here rather than as a field default so it is chosen exactly once,
        # at creation. Every later save reads the stored value and leaves it be.
        extra.setdefault("avatar_url", new_avatar_url())
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class PartnerUser(AbstractBaseUser, PermissionsMixin):
    """A user of the Blossom platform.

    The primary key IS the ``external_user_id`` we hand to Surmount over the SSO
    back-channel. Surmount stores it on ``PartnerSSOIdentity`` and matches on it
    forever after, so it carries two hard requirements:

      * immutable  — it must never change for a given human
      * never reused — it must never be recycled onto a different human

    A UUID primary key satisfies both for free. Matching on email instead would be
    a bug: emails get changed and recycled, and a match on a recycled email would
    hand one person another person's brokerage account.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    avatar_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=(
            "Assigned once at signup and never rewritten. Blank on rows created "
            "before avatars existed; those fall back to the local renderer."
        ),
    )

    objects = PartnerUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Last line of defence for the `picture` claim. ``create_user`` already
        # assigns one, but a row made any other way — the admin, a fixture, a
        # test calling ``objects.create`` — would otherwise reach the ID token
        # with an empty picture. Filling it here means the field is never blank,
        # which is what lets ``picture`` be a plain read with no fallback.
        if not self.avatar_url:
            self.avatar_url = new_avatar_url()
        super().save(*args, **kwargs)

    @property
    def external_user_id(self):
        return str(self.id)

    @property
    def picture(self):
        """Profile picture URL.

        Named ``picture`` because that is the OpenID Connect standard claim for
        it — the same name Google and every other provider uses. Standard names
        are why a relying party needs no Blossom-specific code to read this.

        Assigned once at signup and never recomputed, so it survives a rename and
        does not change under the member.
        """
        return self.avatar_url

