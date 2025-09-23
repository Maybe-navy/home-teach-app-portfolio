# Home Teach App

Home Teach App は、学習塾の運営を支援する Django 製の業務システムです。管理者・講師・生徒向けの 3 つのポータルを備え、授業スケジュール管理からカルテ提出、報酬締めまでを同一アプリで完結できます。ポートフォリオ公開を想定し、安全にデモ公開できる設定やドキュメントも含めています。

## 機能ハイライト
- **管理者ポータル**: 講師・生徒アカウントの発行、担当割り当て、授業スケジュールの編集、教材マスタの一覧・登録・編集、報酬締め処理、CSV / PDF 出力に対応しています。
- **講師ポータル**: 直近授業のダッシュボード表示、授業カルテの下書き・提出、過去授業の検索、教材マスタの登録・編集、授業カルテ PDF のダウンロードが可能です。
- **生徒ポータル**: 自身の授業予定をカレンダー順に閲覧できます。
- **運用補助機能**: デモ用の読み取り専用モード、強制パスワード変更、アクセスログ／ダウンロードログの保存、監査向けミドルウェアなどを実装しています。

## 技術スタック
- Django 5.2 / Python 3.12
- SQLite (標準) ― `.env` で PostgreSQL などに切り替え可能
- Django Templates + Bootstrap + Alpine.js（最小限の動的挙動）
- Pytest による統合テスト (`tests/`)

## ディレクトリ構成
```
admin_portal/   … 管理者向けビュー・フォーム
teacher_portal/ … 講師向けビュー・PDF 出力ユーティリティ
student_portal/ … 生徒向けビュー
personal_info/  … 主要モデル（講師・生徒・授業・カルテ・報酬集計など）
core/           … 共通ロジック（ミドルウェア、ユーザープロファイル、管理コマンド）
docs/           … 運用手順やバックアップに関するドキュメント
```

## 教材マスタ機能

### 概要
- 管理者と講師は `personal_info.TeachingMaterial` を共有し、教材情報を再利用できます。
- 一覧画面は `/materials/`（メニュー内の「教材一覧」）で、常に新着順に並びます。生徒アカウントは閲覧専用、管理者と講師は登録・編集ボタンが表示されます。

### 教材一覧の使い方
1. 管理者はダッシュボードから、講師は授業カルテ編集画面のリンクや直接 URL を開くことでアクセスします。
2. テーブルには教材名・科目・推奨学年・出版社が表示され、登録がない場合は明示的なメッセージが表示されます。
3. 右上の「教材を追加」ボタンと各行の「編集」ボタンは、アクセスしたユーザー種別に合わせて `admin_portal`／`teacher_portal` の URL を自動で利用します。

### 教材の登録
1. 「教材を追加」を選ぶと `personal_info.forms.MaterialList` が表示されます。
2. 必須項目はタイトルと科目です（講師が開いた場合はコード側で `subject` を必須に設定しています）。学年・出版社・備考は任意入力で、全項目は Bootstrap のクラスで整形済みです。
3. 保存すると `created_by` に現在のユーザーが入り、`next` パラメータが指定されている場合はそちらへリダイレクトします。未指定時は教材一覧へ戻ります。

### 教材の編集
- 一覧の各行にある「編集」リンクから、登録時と同じフォームで内容を更新できます。
- `next` パラメータが渡されていると保存後に元の画面へ戻るため、授業カルテ編集中でもスムーズです。

### 授業カルテとの連携
- 講師がカルテを編集すると、担当科目に紐づく教材だけがフォームに表示されます。生徒が過去に使用した教材は優先的に上部へ並びます。
- カルテ提出時に選択した教材は PDF にも反映され、`personal_info.MaterialUsage` として履歴が自動記録されます（重複登録を避けるため `get_or_create` で保存）。

### デモ環境での扱い
- `config.settings_demo`（`DEMO_READ_ONLY=true`）でも教材の登録・編集は許可されています。公開デモで操作例を見せたい際に活用できます。
- データを初期状態に戻したい場合は `python manage.py reset_demo` を定期実行し、教材データや利用履歴を含めてリセットします。

## ローカル開発の始め方
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser  # 管理者アカウントを任意で作成
python manage.py runserver
```

- `.env` の `DJANGO_SECRET_KEY` や `DJANGO_ALLOWED_HOSTS` を自分の環境に合わせて更新してください。
- デモ用の ID を用意したい場合は `python manage.py seed_demo` を実行します（`A_demo` と `T_demo` ユーザーが作成され、パスワードは `Demo!Pass1` です）。必要に応じて管理者ポータルから講師/生徒プロフィールを登録してください。

## Demo モード（公開サンドボックス向け）
デモ公開時は環境変数 `DJANGO_SETTINGS_MODULE=config.settings_demo` を指定して起動します。読み取り専用モードや秘匿管理 URL など、公開運用を想定したハードニングが有効化されます。

```bash
export DJANGO_SETTINGS_MODULE=config.settings_demo
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

| Account | Role | 備考 |
|---------|------|------|
| `A_demo / Demo!Pass1` | スタッフ（非スーパーユーザー） | デモ用管理者。主要機能の編集が可能 |
| `T_demo / Demo!Pass1` | Teacher | 既存授業のカルテ編集が中心。読み取り専用が基本 |

- 許可するホスト名は `DEMO_HOSTS`（複数可）または `DEMO_HOST` で設定します。未設定の場合でも `localhost` / `127.0.0.1` からアクセスできます。
- HTTPS を強制できないローカル検証では `DEMO_FORCE_HTTPS=false` を指定してください。
- デモ用管理サイトは `ADMIN_URL` 環境変数で指定したパスにマウントされます（例: `admin-8c1b3f1c/`）。公開資料に直接記載しないでください。
- `python manage.py reset_demo` でデータベースを初期化し、デモユーザーを再投入できます。定期的な実行で閲覧用データをクリーンに保てます。

## 本番運用のポイント
本番環境では `config/settings_prod.py` を利用し、HTTPS 前提のセキュリティ設定を有効化します。

```bash
export DJANGO_SETTINGS_MODULE=config.settings_prod
export DJANGO_SECRET_KEY="$(openssl rand -hex 64)"
export DJANGO_ALLOWED_HOSTS=app.example.com
export DJANGO_CSRF_TRUSTED_ORIGINS=https://app.example.com

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py check --deploy
```

- `SECURE_SSL_REDIRECT` や HSTS の値は環境変数で上書きできます（`.env.example` を参照）。
- リバースプロキシ経由で TLS を終端する場合は `SECURE_PROXY_SSL_HEADER` が正しく設定されているか確認してください。
- 公開前に `python manage.py check --deploy` を実行し、警告が出ないことを確認してください。

## テスト
```bash
pytest
```

授業カルテ提出フローやアクセス制御など主要ユースケースをカバーする統合テストが含まれています。Pull Request 時の回帰確認に活用できます。

## 補足情報
- デモ環境は原則読み取り専用です。面談などで編集操作を見せる場合はスタッフ権限アカウントを共有し、操作範囲をあらかじめ説明すると安心感を与えられます。
- テンプレートは Bootstrap ベースなので、必要に応じて UI のスクリーンショットを `docs/` 配下に追加すると説明資料が整います。
- 公開環境では `.env` に本番用シークレットを設定し、`DJANGO_DEBUG=False` に変更してください。

---

Happy teaching!
