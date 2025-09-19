from .settings import *  # import base settings
import os
import sys


def _clean_host(value: str) -> str | None:
    host = (value or "").strip()
    if not host:
        return None
    if "://" in host:
        host = host.split("://", 1)[1]
    return host


def _unique(seq):
    seen = set()
    order = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            order.append(item)
    return order


# Demo-safe defaults
DEBUG = False
demo_secret = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY")
if demo_secret:
    SECRET_KEY = demo_secret

raw_hosts = env_list("DEMO_HOSTS")
legacy_host = os.getenv("DEMO_HOST")
if legacy_host:
    raw_hosts.append(legacy_host)
if not raw_hosts:
    raw_hosts = ["localhost", "127.0.0.1"]

clean_hosts = [_clean_host(host) for host in raw_hosts]
clean_hosts = [host for host in clean_hosts if host]
clean_hosts.extend(["localhost", "127.0.0.1"])

ALLOWED_HOSTS = _unique(clean_hosts)


def _build_csrf_origins(hosts):
    origins = []
    for host in hosts:
        if "://" in host:
            origins.append(host)
            continue
        origins.append(f"https://{host}")
        origins.append(f"http://{host}")
    return _unique(origins)


CSRF_TRUSTED_ORIGINS = _build_csrf_origins(ALLOWED_HOSTS)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Read-only mode for non-staff users
DEMO_READ_ONLY = True
# Optional bypass flag (e.g. for automated tests)
DEMO_READ_ONLY_BYPASS = env_bool("DEMO_READ_ONLY_BYPASS", False)

# Static files (for collectstatic on hosts)
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

force_https = env_bool("DEMO_FORCE_HTTPS", True)
_is_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST")) or ("pytest" in sys.modules)
if force_https and not _is_pytest:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Enforce HTTPS behind a proxy in demo (configurable for local runs)
SECURE_SSL_REDIRECT = force_https and not _is_pytest
