"""The signing key behind every ID token Blossom issues.

An ID token is only worth anything because the relying party can prove Blossom
signed it. That proof is asymmetric on purpose: Blossom holds a private key and
never shares it, and publishes the matching *public* key at ``/.well-known/jwks.json``
so anyone can verify a signature without being able to forge one.

That is the single biggest difference between this and a shared-secret hand-off.
A shared secret has to be given to every partner, so every partner can mint
identities for every other partner. A signing key is given to nobody.

Key rotation is why the JWKS endpoint publishes a *set* rather than one key, and
why every token carries a ``kid`` header naming which key signed it: you add the
new key to the set, start signing with it, and only drop the old one once every
token signed with it has expired. Nothing breaks in between.
"""

import logging
import os
from pathlib import Path

from django.conf import settings
from joserfc.jwk import KeySet, RSAKey

logger = logging.getLogger(__name__)

_KEY_SIZE = 2048
_cache = {}


def _key_path() -> Path:
    return Path(settings.OIDC["SIGNING_KEY_PATH"])


def _load_or_create() -> RSAKey:
    """Read the signing key from disk, generating one on first run.

    A real provider takes this from a KMS or a secrets manager and never lets it
    touch a filesystem. Generating it here keeps the mock runnable with no setup,
    which matters because a reference implementation nobody can start is not a
    reference implementation.
    """
    path = _key_path()

    if path.exists():
        key = RSAKey.import_key(path.read_bytes())
    else:
        logger.warning("No OIDC signing key at %s — generating one.", path)
        key = RSAKey.generate_key(_KEY_SIZE, private=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 0600 before the bytes land, not after: a private key must never exist
        # on disk, even briefly, with a mode anyone else can read.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(key.as_pem(private=True))

    # RFC 7638 thumbprint: derived from the key itself, so the same key always
    # gets the same kid — across restarts, across processes, across machines.
    # A random kid would change on every deploy and invalidate every cached JWKS.
    return RSAKey.import_key(
        key.as_pem(private=True),
        parameters={"use": "sig", "alg": "RS256", "kid": key.thumbprint()},
    )


def signing_key() -> RSAKey:
    if "key" not in _cache:
        _cache["key"] = _load_or_create()
    return _cache["key"]


def key_id() -> str:
    return signing_key().kid


def private_key_set() -> KeySet:
    """What the ID token is signed with. Never leaves this process."""
    return KeySet([signing_key()])


def public_jwks() -> dict:
    """What ``/.well-known/jwks.json`` serves.

    ``private=False`` is doing real work here — it strips the private exponent and
    the primes, leaving only the modulus and public exponent. Getting this wrong
    publishes the key that signs every identity on the platform.
    """
    return private_key_set().as_dict(private=False)
