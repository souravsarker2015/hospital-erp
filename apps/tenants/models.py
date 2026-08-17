import uuid

from django.core.validators import RegexValidator
from django.db import models

subdomain_validator = RegexValidator(
    regex=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    message="Subdomain must be lowercase letters, numbers and hyphens only.",
)


class Plan(models.Model):
    """A subscription tier hospitals sign up for. Module flags here only
    describe what a tier includes for pricing-page/marketing purposes —
    actual feature gating in tenant views is a later-phase concern, not
    wired up yet."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    tagline = models.CharField(max_length=120, blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    max_users = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = unlimited")
    includes_pharmacy = models.BooleanField(default=True)
    includes_lab = models.BooleanField(default=False)
    includes_wards = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, help_text="Show a 'Most popular' badge")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "price_monthly"]

    def __str__(self):
        return self.name


class Hospital(models.Model):
    """SaaS tenant. Not a BaseModel: it has no hospital FK of its own and no
    created_by at creation time (the first user doesn't exist yet)."""

    class SubscriptionStatus(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        SUSPENDED = "suspended", "Suspended"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    subdomain = models.SlugField(
        max_length=63, unique=True, validators=[subdomain_validator]
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="hospitals")
    subscription_status = models.CharField(
        max_length=10,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField()
    timezone = models.CharField(max_length=50, default="UTC")
    # Per-hospital MRN counter. Shared-schema means there's no native
    # per-tenant Postgres sequence to lean on, so apps.patients.services
    # increments this under select_for_update() instead.
    last_mrn_number = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """Tracks a hospital's billing relationship with the platform (separate
    from apps.billing, which invoices the hospital's own patients)."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.OneToOneField(Hospital, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.TRIALING)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    # Populated once a real gateway (Stripe or a local processor — TBD) is
    # wired up; the signup flow creates the Subscription without these.
    gateway_customer_id = models.CharField(max_length=120, blank=True)
    gateway_subscription_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.hospital.name} — {self.plan.name} ({self.status})"


class TenantInvoice(models.Model):
    """An invoice from the platform to a hospital for its subscription."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="platform_invoices")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="invoices")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    gateway_reference = models.CharField(max_length=120, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Invoice {self.id} — {self.hospital.name}"
