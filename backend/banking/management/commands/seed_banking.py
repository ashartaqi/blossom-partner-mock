"""Open accounts for members who predate the banking app.

Signup does this going forward. This covers everyone already in the database, so
no member is left with an empty Money page for the accident of having signed up
first. Idempotent — members who already have accounts are skipped.
"""

from django.core.management.base import BaseCommand

from banking.models import Account
from banking.seed import open_accounts
from partner.models import PartnerUser


class Command(BaseCommand):
    help = "Open accounts and post history for members who have none."

    def add_arguments(self, parser):
        parser.add_argument("email", nargs="?", help="Just this member.")

    def handle(self, *args, **options):
        members = PartnerUser.objects.all()
        if options["email"]:
            members = members.filter(
                email=PartnerUser.objects.normalize_email(options["email"])
            )

        opened = skipped = 0
        for member in members:
            if Account.objects.filter(member=member).exists():
                skipped += 1
                continue
            open_accounts(member)
            opened += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Opened accounts for {opened} member(s); {skipped} already had them."
            )
        )
