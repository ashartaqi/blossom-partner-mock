"""Settings for Blossom — the partner banking platform.

A stand-in for Blossom's real backend, built so the hand-off into Surmount can be
developed and tested end to end. It is also the reference implementation Blossom's
own developers can read: the `oidc` app is a working OpenID Provider, and it is
roughly the amount of code standing one up actually takes.

Nothing outside `oidc/` is production-grade. That one deliberately is.
"""

import os
from datetime import timedelta
from pathlib import Path
from corsheaders.defaults import default_headers as cors_default_headers
from urllib.parse import urlsplit

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
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:9000").rstrip("/")

# How the relying party names this provider in its own configuration. Only used
# to render the env block the console hands an integrator.
PARTNER_SLUG = env("PARTNER_SLUG", "blossom")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

# Serving through a tunnel (ngrok, Cloudflare) means requests arrive on a host
# nobody remembered to list, and Django answers with DisallowedHost. Setting
# PUBLIC_BASE_URL is the thing you cannot skip anyway — it becomes the issuer —
# so trust it for the host list too rather than making it two settings that must
# agree.
# A tunnel terminates TLS and forwards over http, so request.scheme reads "http"
# and disagrees with the issuer. Gated on https: only then is there a proxy.
if PUBLIC_BASE_URL.startswith("https://"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

_public_host = urlsplit(PUBLIC_BASE_URL).hostname
if _public_host and _public_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_public_host)

# Tunnels hand out a fresh random hostname every restart, so listing them is not
# possible and DisallowedHost is the first thing anyone testing through one hits.
# A leading dot is Django's wildcard for a domain and its subdomains.
#
# DEBUG only. In production ALLOWED_HOSTS is the check that stops a Host-header
# attack, and a wildcard for somebody else's domain would be a hole in it.
if DEBUG:
    TUNNEL_HOSTS = [".ngrok.app", ".ngrok-free.app", ".ngrok.io", ".trycloudflare.com"]
    ALLOWED_HOSTS += [h for h in TUNNEL_HOSTS if h not in ALLOWED_HOSTS]

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
    "banking",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Directly after SecurityMiddleware, as WhiteNoise requires. Django stops
    # serving static files once DEBUG is off; this puts that job back in-process
    # so one server answers for both the API and the built SPA.
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [BASE_DIR / "templates", BASE_DIR.parent / "frontend" / "dist"],
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
# Where collectstatic gathers everything, and where WhiteNoise serves from.
STATIC_ROOT = BASE_DIR / "staticfiles"
# The SPA build is collected alongside Django's own static files, which is what
# lets one origin serve both. No CORS, and no cross-site cookie to arrange.
_SPA_DIST = BASE_DIR.parent / "frontend" / "dist"
STATICFILES_DIRS = [_SPA_DIST] if _SPA_DIST.exists() else []
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

# The web app sends this to skip ngrok's warning page; not safelisted, so the
# preflight rejects it unless it is allowed here.
CORS_ALLOW_HEADERS = (*cors_default_headers, "ngrok-skip-browser-warning")
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
# Same reasoning as ALLOWED_HOSTS: through a tunnel the browser's origin is the
# public URL, and a CSRF check against a list that only knows localhost rejects
# the sign-in form that starts the whole hand-off.
if PUBLIC_BASE_URL not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(PUBLIC_BASE_URL)
if DEBUG:
    # Matching the ALLOWED_HOSTS wildcards above. CSRF_TRUSTED_ORIGINS needs the
    # scheme, and tunnels are always https.
    CSRF_TRUSTED_ORIGINS += [f"https://*{h}" for h in TUNNEL_HOSTS]

# Lax, not Strict: the authorize request arrives as a top-level GET navigation
# from Surmount's origin, which Lax allows and Strict would silently break —
# the member would be asked to log in again on a platform they are logged into.
# Distinct from Surmount's. Cookies ignore the port, so two Django apps on
# localhost would otherwise share one "sessionid" and overwrite each other.
SESSION_COOKIE_NAME = "blossom_session"
SESSION_COOKIE_HTTPONLY = True

# Lax is correct when the web app and this backend are the same site, which they
# are on localhost — ports do not affect same-site.
#
# Two tunnels put them on different sites, and a Lax cookie is then neither
# stored nor sent on the web app's XHR, so signing in appears to succeed and
# leaves no session. "None" is the fix, and browsers only accept it with Secure,
# so the two move together. Set COOKIE_CROSS_SITE=True when tunnelling.
COOKIE_CROSS_SITE = env_bool("COOKIE_CROSS_SITE", False)
SESSION_COOKIE_SAMESITE = "None" if COOKIE_CROSS_SITE else "Lax"
SESSION_COOKIE_SECURE = COOKIE_CROSS_SITE or not DEBUG
CSRF_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

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
