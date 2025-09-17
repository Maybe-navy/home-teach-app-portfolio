from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse, NoReverseMatch
from .forms import LoginForm, PasswordChangeForm
from .models import UserProfile

#ユーザーIDの接頭字からID種別を識別
def get_user_type_from_username(username):
    prefix = username[:1].upper()
    if prefix == 'A':
        return 'admin'
    elif prefix == 'T':
        return 'teacher'
    elif prefix == 'S':
        return 'student'
    return None

def login_view(request):
    if request.method != 'POST':
        form = LoginForm()
        return render(request, 'core/login.html', {"form": form})

    form = LoginForm(request.POST)
    if not form.is_valid():
        return render(request, 'core/login.html', {"form": form})

    username = form.cleaned_data["username"].strip()
    password = form.cleaned_data["password"]
    expected_user_type = get_user_type_from_username(username)

    # まず認証
    user = authenticate(request, username=username, password=password)

    # 認証失敗時：非管理者であれば失敗回数を加算
    if user is None:
        profile = UserProfile.objects.filter(user__username=username).first()
        if profile and profile.user_type != 'admin':
            profile.failed_login_attempts = (profile.failed_login_attempts or 0) + 1
            if profile.failed_login_attempts >= 4:
                profile.is_locked = True
                messages.error(request, "4回連続でログインに失敗したため、アカウントがロックされました。")
            else:
                messages.error(request, "ユーザー名かパスワードが間違っています。")
            profile.save()
        else:
            messages.error(request, "ユーザー名かパスワードが間違っています。")
        return redirect('core:login')

    # ここから認証成功

    # 1) superuser は最優先で通す（プロフィールが無くても作成）
    if user.is_superuser:
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'user_type': 'admin',
                'is_locked': False,
                'failed_login_attempts': 0,
                'is_temporary_password': False,
            }
        )
        login(request, user)
        return redirect('admin_portal:admin_dashboard')

    # 2) 一般ユーザー用プロフィールを安全に取得/作成
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'user_type': expected_user_type,
            'is_locked': False,
            'failed_login_attempts': 0,
            'is_temporary_password': False,
        }
    )

    # ロック判定
    if profile.is_locked:
        messages.error(request, "アカウントがロックされています。管理者に連絡してください。")
        return redirect('core:login')

    # ユーザー名先頭(A/Tなど)とプロフィール種別の不一致を防ぐ
    if profile.user_type != expected_user_type:
        messages.error(request, "ユーザー種別が一致しません。")
        return redirect('core:login')

    # 失敗回数をリセット
    if profile.failed_login_attempts:
        profile.failed_login_attempts = 0
        profile.save(update_fields=['failed_login_attempts'])

    # ログイン実行
    login(request, user)

    # 一時パスワードなら変更画面へ（講師/生徒のみ強制）
    if profile.is_temporary_password and profile.user_type in ("teacher", "student"):
        return redirect('core:change_password')

    # 種別ごとにダッシュボードへ
    if profile.user_type == "admin":
        return redirect('admin_portal:admin_dashboard')
    elif profile.user_type == "teacher":
        return redirect('teacher_portal:teacher_dashboard')
    elif profile.user_type == "student":
        return redirect('student_dashboard')

    messages.error(request, "ユーザー種別が無効です。")
    return redirect("core:login")


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            new_pw = form.cleaned_data['new_password']
            request.user.set_password(new_pw)
            request.user.save()

            request.user.userprofile.is_temporary_password = False
            request.user.userprofile.save()

            #リダイレクト後にログイン状態維持のため
            login(request, request.user)

            messages.success(request, 'パスワードを変更しました。')

            #ユーザー種別に応じてリダイレクト
            user_type = request.user.userprofile.user_type
            if user_type == 'admin':
                return redirect('admin_portal:admin_dashboard')
            elif user_type == 'teacher':
                return redirect('teacher_portal:teacher_dashboard')
    else:
        form = PasswordChangeForm()
    return render(request, 'core/change_password.html', {'form':form})


from django.http import JsonResponse, HttpResponse
from django.db import connection
import time
from .middleware import (
    REQUESTS_TOTAL,
    ERRORS_TOTAL,
    LATENCY_SUMMARY,
    LATENCY_COUNT,
    _METRICS_LOCK,
)


def health_live(request):
    return JsonResponse({"status": "ok"})


def health_ready(request):
    t0 = time.perf_counter()
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        db_ms = (time.perf_counter() - t0) * 1000
        return JsonResponse({"status": "ready", "db_ms": round(db_ms, 2)})
    except Exception:
        return JsonResponse({"status": "degraded"}, status=503)


def metrics(request):
    out = []
    with _METRICS_LOCK:
        for p, v in REQUESTS_TOTAL.items():
            out.append(f'requests_total{{path="{p}"}} {v}')
        for p, v in ERRORS_TOTAL.items():
            out.append(f'errors_total{{path="{p}"}} {v}')
        for p, s in LATENCY_SUMMARY.items():
            c = max(1, LATENCY_COUNT[p])
            out.append(f'latency_seconds_avg{{path="{p}"}} {s/c:.6f}')
    return HttpResponse("\n".join(out), content_type="text/plain; version=0.0.4")


def home_redirect(request):
    """ロゴクリック時などのホーム遷移先を役割別に振り分ける"""
    if not request.user.is_authenticated:
        try:
            return redirect('core:login')
        except NoReverseMatch:
            return redirect('/auth/login/')

    profile = getattr(request.user, 'userprofile', None)
    role = getattr(profile, 'user_type', None)

    candidates = []
    if role == 'admin':
        candidates = ['admin_portal:admin_dashboard']
    elif role == 'teacher':
        candidates = ['teacher_portal:teacher_dashboard']
    elif role == 'student':
        candidates = ['student_portal:student_dashboard']
    else:
        candidates = ['teacher_portal:teacher_dashboard', 'admin_portal:admin_dashboard']

    candidates += ['core:login']

    for name in candidates:
        try:
            return redirect(reverse(name))
        except NoReverseMatch:
            continue
    return redirect('/')


def error_403(request, exception=None):
    return render(request, '403.html', status=403)


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


def error_500(request):
    return render(request, '500.html', status=500)
