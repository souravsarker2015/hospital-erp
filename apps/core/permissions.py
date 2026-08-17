"""Role/tenant access control for tenant-app views.

Every tenant-app CBV should use RoleRequiredMixin (or, if no role
restriction is needed, TenantMemberRequiredMixin directly); every FBV that
needs role gating should use @role_required. Both close the same gap: a
logged-in user of one hospital hitting another hospital's subdomain with a
guessed URL, which TenantAwareManager alone would not catch on a view that
forgets to scope its queryset.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class TenantMemberRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.hospital is not None
            and request.user.hospital_id != request.hospital.id
        ):
            raise PermissionDenied("This account does not belong to this hospital.")
        return super().dispatch(request, *args, **kwargs)


class RoleRequiredMixin(TenantMemberRequiredMixin, UserPassesTestMixin):
    allowed_roles: list[str] = []

    def test_func(self):
        return self.request.user.role in self.allowed_roles


class PlatformStaffRequiredMixin(LoginRequiredMixin):
    """Gates the platform-owner console (apps.tenants' /platform/ views).

    Mirror image of TenantMemberRequiredMixin: staff managing tenants must
    NOT belong to any one hospital (hospital is null, same as
    createsuperuser accounts), and this is only ever reachable on the bare
    PLATFORM_DOMAIN anyway since /platform/ isn't registered in
    config.urls_tenant — the hospital check here is defense in depth.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not (
            request.user.is_staff and request.user.hospital_id is None
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if (
                request.hospital is not None
                and request.user.hospital_id != request.hospital.id
            ):
                raise PermissionDenied("This account does not belong to this hospital.")
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
