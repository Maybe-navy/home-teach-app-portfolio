from .settings import *  # noqa: F401,F403
import os

# Production defaults
DEBUG = False

if SECRET_KEY == "django-insecure-dev-key":
    raise RuntimeError("DJANGO_SECRET_KEY must be set to a secure value in production.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set for production deployment.")

# HTTPS / security headers
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", True)
SECURE_REFERRER_POLICY = os.environ.get("DJANGO_SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")

# If explicit trusted origins are provided use them, otherwise derive from allowed hosts
_raw_trusted = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if _raw_trusted:
    CSRF_TRUSTED_ORIGINS = _raw_trusted
else:
    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in {"localhost", "127.0.0.1"}]

# Cookie hardening
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Optional: disable Django's browsable error page entirely
fallback_hosts = env_list("DJANGO_FALLBACK_HOSTS")
if fallback_hosts:
    ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS + fallback_hosts))

# Logging: surface security-related warnings to console when LOGGING is configured
LOGGING = globals().get("LOGGING")
if isinstance(LOGGING, dict):
    LOGGING.setdefault("loggers", {})
    LOGGING["loggers"].setdefault("django.security", {
        "handlers": ["console"],
        "level": "WARNING",
        "propagate": True,
    })
