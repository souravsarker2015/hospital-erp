from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".localhost"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# django-browser-reload / debug toolbar can be added here later if wanted.
