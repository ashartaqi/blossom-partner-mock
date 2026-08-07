"""Settings for Blossom — the partner banking platform.

A stand-in for Blossom's real backend, built so the hand-off into Surmount can be
developed and tested end to end. It is also the reference implementation Blossom's
own developers can read: the `oidc` app is a working OpenID Provider, and it is
roughly the amount of code standing one up actually takes.

Nothing outside `oidc/` and `sso/` is production-grade. Those two deliberately are.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, str(default))).lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [v.strip() for v in env(key, default).split(",") if v.strip()]


SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-mock-secret-do-not-ship")

# Where this platform is reachable from a browser — used to build absolute URLs
# for things we hand to another system, like the profile picture claim.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:9000")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "partner",
    "oidc",
    "sso",
    "banking",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "partner.PartnerUser"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "120/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("ACCESS_TOKEN_LIFETIME_MINUTES", 60))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("REFRESH_TOKEN_LIFETIME_DAYS", 7))),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS: only the Blossom web app talks to this backend from a browser. ---
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5300,http://127.0.0.1:5300")
# The web app signs in with credentials:"include" so Django also sets a session
# cookie. /oauth/authorize is a top-level navigation and can only see cookies —
# a bearer token in localStorage is invisible to it.
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Lax, not Strict: the authorize request arrives as a top-level GET navigation
# from Surmount's origin, which Lax allows and Strict would silently break —
# the member would be asked to log in again on a platform they are logged into.
# Distinct from Surmount's. Cookies ignore the port, so two Django apps on
# localhost would otherwise share one "sessionid" and overwrite each other.
SESSION_COOKIE_NAME = "blossom_session"
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Where @login_required sends a browser that reaches /oauth/authorize cold.
LOGIN_URL = "/login/"

# ---------------------------------------------------------------------------
# OpenID Connect provider — the standard path
# ---------------------------------------------------------------------------
# ISSUER is the one value a relying party is configured with. Everything else
# (endpoints, keys, supported algorithms) is read from the discovery document at
# ISSUER/.well-known/openid-configuration, so URLs can move without breaking
# integrations. It is also the `iss` claim in every ID token, and relying parties
# reject a token whose issuer is not an exact match.
OIDC = {
    "ISSUER": env("OIDC_ISSUER", PUBLIC_BASE_URL),
    "SIGNING_KEY_PATH": env("OIDC_SIGNING_KEY_PATH", str(BASE_DIR / "keys" / "oidc_signing_key.pem")),
    # RFC 6749 recommends a maximum of ten minutes for an authorization code and
    # notes that shorter is better. Sixty seconds is enough for two redirects and
    # one back-channel call, and leaves nothing worth stealing from a log.
    "CODE_TTL_SECONDS": int(env("OIDC_CODE_TTL_SECONDS", 60)),
    "SPA_URL": env("OIDC_SPA_URL", "http://localhost:5300"),
}

# Authlib refuses to serve OAuth 2 over plain HTTP, which is the correct default:
# without TLS the authorization code, the client secret and the ID token are all
# readable in transit. Local development and the test suite have no TLS, so the
# documented escape hatch is enabled when — and only when — the issuer is not
# https. A production issuer is https, so this can never be on there.
if not OIDC["ISSUER"].startswith("https://"):
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "1"

AUTHLIB_OAUTH2_PROVIDER = {
    "access_token_generator": True,
    "refresh_token_generator": False,
    # Five minutes. This access token exists to read /userinfo once, during a
    # hand-off that completes in under a second.
    "token_expires_in": {"authorization_code": 300},
}

# ---------------------------------------------------------------------------
# Token exchange — the fallback path, for a platform with no OIDC provider
# ---------------------------------------------------------------------------
# Kept because "stand up an identity provider" is not a small ask for every
# partner. Two endpoints, a shared secret, the same one-time-code shape. Weaker
# than OIDC in one specific way: the secret is symmetric, so both sides can mint
# what the other verifies. Use OIDC unless you cannot.
SSO = {
    "CLIENT_ID": env("SSO_CLIENT_ID", "surmount-blossom"),
    "CLIENT_SECRET": env("SSO_CLIENT_SECRET", "dev-shared-secret-change-me"),
    "CODE_TTL_SECONDS": int(env("SSO_CODE_TTL_SECONDS", 60)),
    # Exact-match allow-list. Without it /sso/initiate is an open redirect that
    # hands a valid identity code to whatever host the caller names.
    "ALLOWED_REDIRECT_URIS": env_list(
        "SSO_ALLOWED_REDIRECT_URIS",
        "http://localhost:8000/api/sso/blossom/token-exchange/callback/",
    ),
    "DEFAULT_REDIRECT_URI": env(
        "SSO_DEFAULT_REDIRECT_URI",
        "http://localhost:8000/api/sso/blossom/token-exchange/callback/",
    ),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "loggers": {
        # Every hand-off decision is audited here — minted, redeemed, rejected and
        # why. In production this handler ships somewhere durable and searchable;
        # an audit log with no sink is not an audit log.
        "sso.audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
