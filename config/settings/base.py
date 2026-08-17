from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "django_htmx",
    # local — shared/public side (not scoped to a Hospital)
    "apps.core",
    "apps.users",
    "apps.tenants",
    "apps.marketing",
    # local — tenant side (scoped to a Hospital via TenantAwareManager)
    "apps.dashboard",
    "apps.patients",
    "apps.appointments",
    "apps.clinical",
    "apps.pharmacy",
    "apps.lab",
    "apps.billing",
    "apps.wards",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.CurrentHospitalMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.current_hospital",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "marketing:home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- root domain used to resolve <subdomain>.<PLATFORM_DOMAIN> to a Hospital ---
# In dev this is "localhost" so e.g. citycare.localhost:8000 resolves without
# any /etc/hosts editing (modern browsers/OS resolve *.localhost to 127.0.0.1).
PLATFORM_DOMAIN = env("PLATFORM_DOMAIN", default="localhost")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@hospital-erp.local")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# --- celery ---
# CELERY_TASK_ASYNC_ENABLED=true dispatches through Celery for real (needs a
# broker + worker running); false (default everywhere until turned on) runs
# task bodies synchronously inline instead, no broker required.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_ASYNC_ENABLED = env.bool("CELERY_TASK_ASYNC_ENABLED", default=False)
CELERY_TASK_ALWAYS_EAGER = not CELERY_TASK_ASYNC_ENABLED
CELERY_TASK_EAGER_PROPAGATES = True

# --- structured logging: one logger per app, hospital_id/user_id on every line ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "context_defaults": {"()": "apps.core.logging_utils.ContextDefaultsFilter"},
    },
    "formatters": {
        "structured": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s %(message)s "
                "hospital_id=%(hospital_id)s user_id=%(user_id)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["context_defaults"],
            "formatter": "structured",
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        app: {"handlers": ["console"], "level": "INFO", "propagate": False}
        for app in (
            "core",
            "users",
            "tenants",
            "marketing",
            "dashboard",
            "patients",
            "appointments",
            "clinical",
            "pharmacy",
            "lab",
            "billing",
            "wards",
        )
    },
}
