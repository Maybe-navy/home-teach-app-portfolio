from django.http import HttpResponseNotAllowed
from django.conf import settings


class ReadOnlyMiddleware:
    SAFE = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        demo = getattr(settings, "DEMO_READ_ONLY", False)
        if demo and request.method not in self.SAFE:
            # Allow login/logout POSTs so users can sign in/out in demo
            path = (request.path or "")
            if path.endswith("/login/") or path.endswith("/logout/"):
                return self.get_response(request)

            user = getattr(request, "user", None)
            if not (getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False)):
                return HttpResponseNotAllowed(self.SAFE)
        return self.get_response(request)
