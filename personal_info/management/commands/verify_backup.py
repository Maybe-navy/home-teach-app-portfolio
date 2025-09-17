import os, json, tarfile
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "backups/ ディレクトリのバックアップセットを簡易検証（JSONの整合、tar の展開可否のみ）"

    def add_arguments(self, parser):
        parser.add_argument("--date", help="YYYY-MM-DD の日付で特定（省略時は最新）")

    def handle(self, *args, **opts):
        base = "backups"
        if not os.path.isdir(base):
            raise CommandError("backups ディレクトリがありません")
        files = sorted(os.listdir(base))
        jsons = [f for f in files if f.startswith("data-") and f.endswith(".json")]
        tars = [f for f in files if f.startswith("media-") and f.endswith(".tar.gz")]
        if not jsons:
            raise CommandError("データJSONが見つかりません")
        if not tars:
            self.stdout.write(self.style.WARNING("メディアtarが見つかりません（媒体未使用ならOK）"))
        target_json = os.path.join(base, jsons[-1])
        with open(target_json, "r", encoding="utf-8") as fp:
            json.load(fp)
        if tars:
            tarpath = os.path.join(base, tars[-1])
            with tarfile.open(tarpath, "r:gz") as tf:
                tf.getmembers()[:1]
        self.stdout.write(self.style.SUCCESS(f"OK: {target_json} / {tars[-1] if tars else 'no-media'}"))
