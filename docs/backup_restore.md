# バックアップ / リストア手順

## DB (SQLite/PostgreSQL)
### SQLite
- 退避: `cp db.sqlite3 backups/db-$(date +%F).sqlite3`
- 復元: `cp backups/db-YYYY-MM-DD.sqlite3 db.sqlite3`

### PostgreSQL
- 退避: `pg_dump $DATABASE_URL > backups/db-$(date +%F).sql`
- 復元: `psql $DATABASE_URL < backups/db-YYYY-MM-DD.sql`

## Django データ (汎用)
- 退避: `python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > backups/data-$(date +%F).json`
- 復元: `python manage.py loaddata backups/data-YYYY-MM-DD.json`

## メディア
- 退避: `tar czf backups/media-$(date +%F).tar.gz media/`
- 復元: `tar xzf backups/media-YYYY-MM-DD.tar.gz -C .`

## 推奨運用
- DBとメディアを**同じ日付**でペアにする
- 復元前にアプリをメンテナンスモードに
- 復元後は`/health/ready`で確認、重要導線を目視確認

