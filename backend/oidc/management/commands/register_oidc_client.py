"""Register (or update) a relying party.

This is what onboarding a partner actually is: one row, one secret handed over on
a secure channel, done. There is no code change, no deploy, and no per-partner
branch anywhere in the provider — which is the whole reason for using the standard
rather than inventing an integration per client.

    manage.py register_oidc_client \\
        --client-id surmount-blossom \\
        --name "Surmount Investing" \\
        --redirect-uri http://localhost:8000/api/sso/blossom/callback/ \\
        --trusted
"""

from django.core.management.base import BaseCommand, CommandError

from oidc.models import OAuth2Client, generate_client_secret


class Command(BaseCommand):
    help = "Register or update an OAuth2 / OIDC client."

    def add_arguments(self, parser):
        parser.add_argument("--client-id", required=True)
        parser.add_argument("--name", default="")
        parser.add_argument(
            "--redirect-uri",
            action="append",
            default=[],
            dest="redirect_uris",
            help="Repeatable. Matched exactly at /oauth/authorize.",
        )
        parser.add_argument(
            "--post-logout-redirect-uri", action="append", default=[],
            dest="post_logout_redirect_uris",
        )
        parser.add_argument("--scope", default="openid profile email")
        parser.add_argument(
            "--trusted",
            action="store_true",
            help="First-party client: skip the consent screen.",
        )
        parser.add_argument(
            "--secret",
            default=None,
            help="Use this secret instead of generating one. For reproducible local setup only.",
        )
        parser.add_argument(
            "--rotate-secret",
            action="store_true",
            help="Issue a new secret for an existing client.",
        )

    def handle(self, *args, **options):
        client_id = options["client_id"]
        client = OAuth2Client.objects.filter(client_id=client_id).first()
        created = client is None

        if created:
            client = OAuth2Client(client_id=client_id)
        elif not options["rotate_secret"] and not options["secret"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{client_id} already exists — updating settings, keeping the secret."
                )
            )

        if options["redirect_uris"]:
            client.redirect_uris = "\n".join(options["redirect_uris"])
        elif created:
            raise CommandError("A new client needs at least one --redirect-uri.")

        if options["post_logout_redirect_uris"]:
            client.post_logout_redirect_uris = "\n".join(
                options["post_logout_redirect_uris"]
            )

        client.client_name = options["name"] or client.client_name or client_id
        client.scope = options["scope"]
        client.is_trusted = options["trusted"] or client.is_trusted
        # No refresh-token grant: see the note in oidc/server.py.
        client.grant_types = "authorization_code"
        client.response_types = "code"

        secret = None
        if created or options["rotate_secret"] or options["secret"]:
            secret = options["secret"] or generate_client_secret()
            client.set_secret(secret)

        client.save()

        self.stdout.write(
            self.style.SUCCESS(f"{'Registered' if created else 'Updated'} {client_id}")
        )
        for uri in client.redirect_uris.splitlines():
            self.stdout.write(f"  redirect_uri  {uri}")
        self.stdout.write(f"  scope         {client.scope}")
        self.stdout.write(f"  trusted       {client.is_trusted}")

        if secret:
            # Printed here and nowhere else, ever. Only the SHA-256 digest is
            # stored, so this value cannot be recovered — it can only be replaced.
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("  client_secret (shown once):"))
            self.stdout.write(f"  {secret}")
