from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from personal_info.models import AccessLog


class Command(BaseCommand):
    help = "AccessLog を一定日数より前のものを削除（デフォルト90日）"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90)

    def handle(self, *args, **opts):
        days = opts["days"]
        cutoff = timezone.now() - timedelta(days=days)
        qs = AccessLog.objects.filter(created_at__lt=cutoff)
        n = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {n} AccessLog entries older than {days} days."))
