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

Every member has one: ``create_user`` assigns it, and ``PartnerUser.save``
backstops anything created another way. There is no fallback renderer and no
avatar route on this service — the claim is simply the stored URL.
"""

import secrets

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
