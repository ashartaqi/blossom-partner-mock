"""Give a member access to the provider console.

The console can register clients and rotate secrets, so it is staff-only. Members
sign in through the same app, which is exactly why it cannot simply check "is
logged in" — that would hand every member of the platform the provider's
controls.

    manage.py grant_console alice@blossom.test
    manage.py grant_console --all          # local convenience, never in staging
"""

from django.core.management.base import BaseCommand, CommandError

from partner.models import PartnerUser


class Command(BaseCommand):
    help = "Grant (or revoke) provider-console access for a member."

    def add_arguments(self, parser):
        parser.add_argument("email", nargs="?", default=None)
        parser.add_argument(
            "--all",
            action="store_true",
            help="Every member. For a throwaway local database only.",
        )
        parser.add_argument(
            "--revoke", action="store_true", help="Take the access away again."
        )

    def handle(self, *args, **options):
        grant = not options["revoke"]

        if options["all"]:
            count = PartnerUser.objects.update(is_staff=grant)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Granted' if grant else 'Revoked'} console access for {count} members."
                )
            )
            return

        email = options["email"]
        if not email:
            raise CommandError("Give an email address, or --all.")

        user = PartnerUser.objects.filter(email=PartnerUser.objects.normalize_email(email)).first()
        if not user:
            raise CommandError(f"No member with email {email}.")

        user.is_staff = grant
        user.save(update_fields=["is_staff"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Granted' if grant else 'Revoked'} console access for {user.email}."
            )
        )
