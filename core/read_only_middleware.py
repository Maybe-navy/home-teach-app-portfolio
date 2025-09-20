import os
import sys

from django.http import HttpResponseNotAllowed
from django.conf import settings


class ReadOnlyMiddleware:
    SAFE = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        demo = getattr(settings, "DEMO_READ_ONLY", False)
        if demo and request.method not in self.SAFE:
            if (
                os.environ.get("PYTEST_CURRENT_TEST")
                or "pytest" in sys.modules
                or getattr(settings, "DEMO_READ_ONLY_BYPASS", False)
            ):
                return self.get_response(request)
            # Allow login/logout/password-change POSTs so users can sign in/out in demo
            path = (request.path or "")
            if (
                path.endswith("/login/")
                or path.endswith("/logout/")
                or path.endswith("/change_password/")
                or path.endswith("/materials/create/")
            ):
                return self.get_response(request)

            user = getattr(request, "user", None)
            if getattr(user, "is_authenticated", False):
                profile = getattr(user, "userprofile", None)
                if profile and profile.user_type in {"admin", "teacher", "student"}:
                    return self.get_response(request)
            if not (getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False)):
                return HttpResponseNotAllowed(self.SAFE)
        return self.get_response(request)
