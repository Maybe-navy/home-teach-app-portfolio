from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class ForcePasswordChangeMiddleware(MiddlewareMixin):
    """ユーザー種別ごとのハイブリッド強制パスワード変更ミドルウェア"""

    def process_request(self, request):
        if not getattr(settings, "REQUIRE_PASSWORD_CHANGE_ON_FIRST_LOGIN", True):
            return

        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return

        profile = getattr(user, "userprofile", None)
        if not profile:
            return

        if profile.user_type == "admin":
            return

        if profile.user_type not in ("teacher", "student"):
            return

        if not getattr(profile, "is_temporary_password", False):
            return

        current_name = None
        if request.resolver_match:
            current_name = request.resolver_match.view_name

        allowed_names = {"core:change_password", "core:login", "logout"}
        allowed_prefixes = ("/static/", "/media/", "/admin/")

        path = request.path or "/"
        if current_name in allowed_names or any(path.startswith(p) for p in allowed_prefixes):
            return

        change_url = reverse("core:change_password")
        return redirect(f"{change_url}?next={path}")
