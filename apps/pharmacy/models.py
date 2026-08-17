from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.core.models import TenantScopedModel

EXPIRING_SOON_DAYS = 30


class Drug(TenantScopedModel):
    class Unit(models.TextChoices):
        TABLET = "tablet", "Tablet"
        CAPSULE = "capsule", "Capsule"
        SYRUP = "syrup", "Syrup"
        INJECTION = "injection", "Injection"
        OINTMENT = "ointment", "Ointment"
        DROPS = "drops", "Drops"
        INHALER = "inhaler", "Inhaler"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    strength = models.CharField(max_length=50, blank=True, help_text="e.g. 500mg")
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.TABLET)
    low_stock_threshold = models.PositiveIntegerField(default=20)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Price per unit dispensed")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "name", "strength"], name="unique_drug_per_hospital"),
        ]

    def __str__(self):
        return f"{self.name} {self.strength}".strip()

    @property
    def total_available_stock(self) -> int:
        return (
            self.batches.filter(expiry_date__gte=timezone.localdate())
            .aggregate(total=Sum("quantity_remaining"))["total"]
            or 0
        )

    @property
    def is_low_stock(self) -> bool:
        return self.total_available_stock <= self.low_stock_threshold


class StockBatch(TenantScopedModel):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    quantity_received = models.PositiveIntegerField()
    quantity_remaining = models.PositiveIntegerField()
    supplier = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["expiry_date"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "drug", "batch_number"], name="unique_batch_per_drug"),
        ]

    def __str__(self):
        return f"{self.drug} — batch {self.batch_number}"

    @property
    def is_expired(self) -> bool:
        return self.expiry_date < timezone.localdate()

    @property
    def is_expiring_soon(self) -> bool:
        days_left = (self.expiry_date - timezone.localdate()).days
        return 0 <= days_left <= EXPIRING_SOON_DAYS


class StockMovement(TenantScopedModel):
    class MovementType(models.TextChoices):
        STOCK_IN = "stock_in", "Stock In"
        DISPENSE = "dispense", "Dispense"
        ADJUSTMENT = "adjustment", "Adjustment"

    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name="movements")
    batch = models.ForeignKey(StockBatch, on_delete=models.CASCADE, related_name="movements", null=True, blank=True)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField(help_text="Positive for stock in, negative for dispense/adjustment out")
    notes = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} — {self.drug}"


class DispenseRecord(TenantScopedModel):
    prescription_item = models.OneToOneField(
        "clinical.PrescriptionItem", on_delete=models.CASCADE, related_name="dispense_record"
    )
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="dispense_records")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="dispense_records")
    quantity = models.PositiveIntegerField()
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    def __str__(self):
        return f"{self.drug.name} x{self.quantity} for {self.prescription_item}"
