"""Profile pictures.

Real platforms let members upload one. This mock assigns one automatically, from
DiceBear — a free, keyless avatar API that renders a deterministic image for a
given style and seed.

Two properties matter, and they pull in opposite directions:

  * **Random per member.** Two members who sign up seconds apart should not get
    near-identical pictures. Hence a random style *and* a random seed, drawn at
    signup rather than derived from the email or the name.

  * **Permanent once assigned.** A picture that changed when a member renamed
    themselves — or worse, on every page load — would be a bug. So the finished
    URL is written to the row at signup and simply read back after that. Nothing
    recomputes it, which also means editing this file never disturbs a picture
    that has already been handed out.

The local SVG renderer below stays as the fallback: it covers members created
before this, and working with no network.
"""

import hashlib
import secrets

from django.http import HttpResponse

DICEBEAR_BASE = "https://api.dicebear.com/9.x"

# Styles that read as a person and stay legible at 28px, the size the topbar
# renders them at. Deliberately excludes the abstract-shape styles — at avatar
# size those turn into indistinguishable blobs.
STYLES = (
    "adventurer",
    "avataaars",
    "big-smile",
    "lorelei",
    "micah",
    "notionists",
    "open-peeps",
    "personas",
)

# Backgrounds are set explicitly rather than left transparent, so an avatar keeps
# its shape against both the white topbar and the tinted sidebar.
BACKGROUNDS = "b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf"


def new_avatar_url():
    """A fresh random avatar URL. Called once, at signup.

    The seed is random rather than the member's id or email: seeding from an
    identifier would make the picture derivable from public data, and would give
    two members with similar identifiers similar images.

    PNG rather than SVG, deliberately. Consumers put this straight into an image
    tag, and an SVG from a third-party host is a script-execution vector — which
    is why Next.js refuses to serve one through its optimizer unless you set a
    flag with "dangerously" in the name. A raster format makes the question moot
    for everyone downstream.
    """
    style = secrets.choice(STYLES)
    seed = secrets.token_hex(8)
    return (
        f"{DICEBEAR_BASE}/{style}/png"
        f"?seed={seed}&backgroundColor={BACKGROUNDS}&radius=50&size=128"
    )


# ---------------------------------------------------------------------------
# Local fallback — no network required
# ---------------------------------------------------------------------------

# Picked to stay legible with white text on top.
PALETTE = [
    "#C2557F", "#0E6068", "#A96F14", "#5B5BD6",
    "#2E7D53", "#B0473C", "#6D5BA6", "#1F6FB2",
]


def _initials(user):
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    letters = f"{first[:1]}{last[:1]}".upper()
    return letters or (user.email[:1].upper() if user.email else "?")


def _colour(seed):
    # Hash rather than a counter so the colour is stable across restarts and
    # doesn't depend on how many users exist.
    digest = hashlib.sha256(str(seed).encode()).digest()
    return PALETTE[digest[0] % len(PALETTE)]


def avatar_svg(request, user_id):
    """GET /avatar/<user_id>.svg — initials on a colour derived from the id."""
    from partner.models import PartnerUser

    user = PartnerUser.objects.filter(id=user_id).first()
    initials = _initials(user) if user else "?"
    colour = _colour(user_id)

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" '
        'viewBox="0 0 128 128" role="img">'
        f'<rect width="128" height="128" rx="64" fill="{colour}"/>'
        '<text x="64" y="64" fill="#fff" font-size="52" font-weight="600" '
        'font-family="system-ui, -apple-system, Segoe UI, sans-serif" '
        f'text-anchor="middle" dominant-baseline="central">{initials}</text>'
        "</svg>"
    )

    response = HttpResponse(svg, content_type="image/svg+xml")
    response["Cache-Control"] = "public, max-age=3600"
    return response
