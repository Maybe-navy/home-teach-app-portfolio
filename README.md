![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg?branch=public)

![Release](https://img.shields.io/github/v/release/<owner>/<repo>?include_prereleases&label=release)


# Home Teach App

Home Teach App は、学習塾の運営を想定した Django 製の業務支援システムです。管理者・講師・生徒の 3 つのポータルを備え、授業スケジュール、カルテ提出、報酬計算、アカウント管理が 1 つのアプリで完結します。本リポジトリはポートフォリオ公開を想定した安全な構成とドキュメントを含みます。

## Overview

- **Multi-portal UI**: `/admin_portal`, `/teacher_portal`, `/student_portal` で役割に応じたダッシュボードを提供。
- **Reward & schedule operations**: 授業カルテの提出状況に応じて報酬を集計し、締め処理や PDF 出力が可能。
- **Hardening for demos**: 読み取り専用モード、強制パスワード変更、監査ログなどコンプライアンス機能を内蔵。
- **Bilingual docs**: 英語 / 日本語でセットアップ手順を用意し、公開デモや面談時の説明に活用できます。

## Tech Stack

- Django 5.2 / Python 3.12
- SQLite (デフォルト) — `.env` で他の DB に切り替え可能
- HTML templates + Bootstrap + Alpine.js (最小限のインタラクション)
- Pytest ベースの統合テスト (`tests/`)

## Project Structure

```
admin_portal/  … 管理者向け機能（登録、報酬締め、PDF 出力 など）
teacher_portal/ … 授業カルテ提出やスケジュール調整
student_portal/ … 生徒用の閲覧 UI
personal_info/ … ドメインモデル（TeacherProfile, ClassSchedule, …）
core/          … 共通ロジック（ミドルウェア、ユーティリティ、管理コマンド）
docs/          … 運用手順やバックアップドリル
```

## Quickstart (Local Development)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- `.env` の `DJANGO_SECRET_KEY`、`DJANGO_ALLOWED_HOSTS` を自身の環境に合わせて変更。
- `python manage.py createsuperuser` で開発用のアカウントを作成（任意で `seed_demo` コマンドを実行するとデモデータを投入可能）。

## Demo Mode (Optional Public Sandbox)

デモ公開時は環境変数 `DJANGO_SETTINGS_MODULE=config.settings_demo` を指定して起動します。読み取り専用モードや管理画面の秘匿 URL など、公開前提でのハードニングが有効化されます。

```bash
export DJANGO_SETTINGS_MODULE=config.settings_demo
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

| Account | Role | Notes |
|---------|------|-------|
| `A_demo / Demo!Pass1` | Staff (non-superuser) | 書き込みが可能な仮管理者 |
| `T_demo / Demo!Pass1` | Teacher | 読み取り専用が基本 |

- ホスト名は `DEMO_HOSTS` (複数可) または `DEMO_HOST` で指定できます。未設定時でも `localhost` / `127.0.0.1` からアクセスできます。
- HTTPS を強制できないローカル検証では `DEMO_FORCE_HTTPS=false` を指定してください。
- デモ用管理サイトは `ADMIN_URL` 環境変数で指定したパスにマウントされます（例: `admin-8c1b3f1c/`）。公開資料に直接記載しないでください。
- `python manage.py reset_demo` で DB の初期化とデモデータの再投入が実行されます。cron を利用して定期実行することで閲覧用データをクリーンに保てます。

## Production Deployment

本番運用時は `config/settings_prod.py` を利用し、HTTPS 前提のセキュリティ設定を有効化します。

```bash
export DJANGO_SETTINGS_MODULE=config.settings_prod
export DJANGO_SECRET_KEY="$(openssl rand -hex 64)"
export DJANGO_ALLOWED_HOSTS=app.example.com
export DJANGO_CSRF_TRUSTED_ORIGINS=https://app.example.com

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py check --deploy
```

- `SECURE_SSL_REDIRECT` / HSTS などの値は環境変数で上書き可能です（`.env.example` を参照）。
- リバースプロキシ経由で TLS 終端する場合は `SECURE_PROXY_SSL_HEADER` が適切に設定されているか確認してください。
- 上記コマンドは Django を公開する前に一度実行し、警告が解消されていることを確認します。

## Running Tests

```bash
pytest
```

代表的なユースケース（カルテ提出、報酬締め、アクセス制御 など）をカバーする統合テストを含みます。Pull Request での品質担保に利用してください。

## Portfolio Tips

- デモ環境は read-only が基本のため、面談ではスタッフ権限アカウントを共有し、特定の機能のみ編集できる点を説明すると安心感を与えられます。
- テンプレートは Bootstrap ベースなので、必要に応じて UI スクリーンショットを `docs/` 配下に追加すると説明資料が整います。
- デプロイ時は `.env` に本番用シークレットを設定し、`DJANGO_DEBUG=False` に変更してください。

## 日本語セットアップガイド

1. `python -m venv venv` → `source venv/bin/activate`
2. `pip install -r requirements.txt`
3. `.env.example` を `.env` にコピーし、`DJANGO_SECRET_KEY` を任意の値に変更
4. `python manage.py migrate`
5. `python manage.py seed_demo` または `python manage.py createsuperuser`
6. `python manage.py runserver 127.0.0.1:8000`

注意: 公開デモの場合は個人情報を入力しないよう、README や実際の画面に注意書きを表示してください。

---

Happy teaching!
