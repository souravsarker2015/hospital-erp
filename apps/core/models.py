import uuid

from django.conf import settings
from django.db import models

from apps.core.middleware import get_current_hospital


class BaseModel(models.Model):
    """Abstract base every domain model inherits: UUID pk + audit fields."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class TenantAwareQuerySet(models.QuerySet):
    def for_hospital(self, hospital):
        return self.filter(hospital=hospital)


class TenantAwareManager(models.Manager):
    """Auto-scopes to the hospital resolved by CurrentHospitalMiddleware for
    the in-flight request. Outside a request (management commands, shell,
    tests, platform-side super-admin code) there is no current hospital, so
    this returns every tenant's rows unfiltered by design — that code is
    expected to filter explicitly. Never call this manager from a
    tenant-facing view without having gone through the middleware first."""

    def get_queryset(self):
        qs = TenantAwareQuerySet(self.model, using=self._db)
        hospital = get_current_hospital()
        if hospital is not None:
            qs = qs.filter(hospital=hospital)
        return qs


class TenantScopedModel(BaseModel):
    """Abstract base for every clinical/tenant-app model: carries the
    Hospital FK and defaults `objects` to the auto-scoping manager.
    `all_hospitals` is the explicit, clearly-named escape hatch for
    cross-tenant code (platform admin, migrations, management commands)."""

    hospital = models.ForeignKey(
        "tenants.Hospital", on_delete=models.CASCADE, related_name="+"
    )

    objects = TenantAwareManager()
    all_hospitals = models.Manager()

    class Meta(BaseModel.Meta):
        abstract = True
