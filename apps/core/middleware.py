"""Thread-local current hospital + user.

Two consumers:
- apps.core.models.TenantAwareManager reads get_current_hospital() so any
  `Model.objects` query issued during a request is scoped to that hospital
  without every view/service remembering to add `.filter(hospital=...)`.
- signal handlers / services with no request object (e.g. Celery tasks
  invoked synchronously mid-request) can still attribute rows via
  get_current_user().

This is defense in depth, not the isolation boundary itself: the hard
boundary is CurrentHospitalMiddleware resolving exactly one hospital per
subdomain and view-level role mixins refusing access when
request.user.hospital != request.hospital.
"""

import threading

from django.shortcuts import get_object_or_404

_thread_locals = threading.local()


def get_current_hospital():
    return getattr(_thread_locals, "hospital", None)


def get_current_user():
    user = getattr(_thread_locals, "user", None)
    if user is not None and user.is_authenticated:
        return user
    return None


class CurrentHospitalMiddleware:
    """Resolves the subdomain of the request host to a Hospital and attaches
    it as request.hospital (None on the bare PLATFORM_DOMAIN, where the
    marketing site and platform admin live)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        from apps.tenants.models import Hospital

        host = request.get_host().split(":")[0]
        platform_domain = settings.PLATFORM_DOMAIN
        request.hospital = None

        if host != platform_domain and host.endswith(f".{platform_domain}"):
            subdomain = host[: -len(f".{platform_domain}")]
            if subdomain not in ("www", "app"):
                request.hospital = get_object_or_404(
                    Hospital, subdomain=subdomain, is_active=True
                )

        if request.hospital is not None:
            request.urlconf = "config.urls_tenant"

        _thread_locals.hospital = request.hospital
        _thread_locals.user = getattr(request, "user", None)
        try:
            return self.get_response(request)
        finally:
            _thread_locals.hospital = None
            _thread_locals.user = None
