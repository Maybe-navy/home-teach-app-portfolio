from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Alias for daily demo reset; calls reset_demo. Schedule this daily via cron."

    def handle(self, *args, **opts):
        call_command("reset_demo")
        self.stdout.write(self.style.SUCCESS("Daily demo reset executed."))

