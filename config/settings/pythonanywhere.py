from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = False
SECRET_KEY = env("SECRET_KEY")

# Replace <username> with the actual PythonAnywhere account name (or set
# ALLOWED_HOSTS in the .env on the server).
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["<username>.pythonanywhere.com"])

# sqlite is fine for demo/staging traffic on PythonAnywhere. Note this is a
# shared-schema app (every tenant row carries a Hospital FK, no per-tenant
# Postgres schema), so sqlite here does NOT compromise tenant isolation the
# way it would under django-tenants — isolation is enforced by
# apps.core.TenantAwareManager regardless of DB engine. sqlite still
# serializes writes (one writer at a time) though, so move to the
# Postgres-backed prod.py settings before real concurrent production load.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Celery has no broker on PythonAnywhere's free/hacker tiers; run tasks
# inline instead of dispatching to a worker that doesn't exist.
CELERY_TASK_ALWAYS_EAGER = True

# PythonAnywhere static files mapping: URL /static/ -> directory {BASE_DIR}/staticfiles
# (run `manage.py collectstatic` on the server after each deploy).
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
