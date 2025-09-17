from .settings import *  # import base settings
import os

# Demo-safe defaults
DEBUG = False
demo_secret = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY")
if demo_secret:
    SECRET_KEY = demo_secret
demo_host = os.getenv("DEMO_HOST", "localhost")
ALLOWED_HOSTS = [demo_host]
CSRF_TRUSTED_ORIGINS = [f"https://{demo_host}"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Read-only mode for non-staff users
DEMO_READ_ONLY = True

# Production-ish cookie settings for demo behind proxy/https
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files (for collectstatic on hosts)
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Enforce HTTPS behind a proxy in demo
SECURE_SSL_REDIRECT = True
