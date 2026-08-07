from django.db import migrations


def svg_to_png(apps, schema_editor):
    """Re-point existing avatars at the PNG endpoint.

    This does not change anyone's picture. DiceBear renders from the style and
    the seed, and both are untouched — the same character comes back, in a raster
    format instead of a vector one. Only the encoding moves.

    Needed because consumers render this URL in an image tag, and an SVG from a
    third-party host is a script-execution vector. Next.js will not put one
    through its image optimizer without an explicitly "dangerous" flag, so the
    fix belongs here, at the source, rather than in every consumer.
    """
    PartnerUser = apps.get_model("partner", "PartnerUser")
    for user in PartnerUser.objects.filter(avatar_url__contains="/svg?"):
        user.avatar_url = (
            user.avatar_url.replace("/svg?", "/png?") + "&size=128"
        )
        user.save(update_fields=["avatar_url"])


def png_to_svg(apps, schema_editor):
    PartnerUser = apps.get_model("partner", "PartnerUser")
    for user in PartnerUser.objects.filter(avatar_url__contains="/png?"):
        user.avatar_url = user.avatar_url.replace("/png?", "/svg?").replace(
            "&size=128", ""
        )
        user.save(update_fields=["avatar_url"])


class Migration(migrations.Migration):

    dependencies = [
        ("partner", "0002_partneruser_avatar_url"),
    ]

    operations = [
        migrations.RunPython(svg_to_png, png_to_svg),
    ]
