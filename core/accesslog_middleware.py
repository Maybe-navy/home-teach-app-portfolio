from .models import AccessLog


class AccessLogMiddleware:
    """リクエスト/レスポンスをDBへ記録"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, "user", None)
            role = ""
            if user and user.is_authenticated and hasattr(user, "userprofile"):
                role = user.userprofile.user_type
            AccessLog.objects.create(
                user=user if user and user.is_authenticated else None,
                role=role,
                method=request.method,
                path=request.path[:512],
                status=getattr(response, "status_code", 0),
                ip=(request.META.get("REMOTE_ADDR") or "")[:45],
                ua=(request.META.get("HTTP_USER_AGENT") or "")[:1000],
                referer=(request.META.get("HTTP_REFERER") or "")[:1000],
            )
        except Exception:
            pass
        return response
