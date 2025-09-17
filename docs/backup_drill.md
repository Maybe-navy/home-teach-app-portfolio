# バックアップ演習手順

1. 週1で `dumpdata` とメディアを `backups/` へ退避。
2. `python manage.py verify_backup` を実行し整合性を確認。
3. 復元演習時はメンテナンスモードにし、データとメディアをリストア。
4. `python manage.py migrate` 後 `/health/ready` を確認。
5. 主要導線を手動で確認し完了を記録。
