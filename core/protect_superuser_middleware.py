from django.http import HttpResponseForbidden
from django.urls import resolve


PROTECT_NAMES = {"admin", "superuser"}


class ProtectSuperuserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            try:
                name = (resolve(request.path_info).url_name or "").lower()
            except Exception:
                name = ""
            if "user" in name or "profile" in name or "account" in name:
                target_username = (request.POST.get("username") or "").lower()
                if target_username in PROTECT_NAMES:
                    return HttpResponseForbidden("Protected user")
        return self.get_response(request)

