from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Flush DB, migrate, and seed demo data."

    def handle(self, *args, **opts):
        call_command("flush", interactive=False)
        call_command("migrate", interactive=False)
        call_command("seed_demo")
        self.stdout.write(self.style.SUCCESS("Demo reset complete."))

