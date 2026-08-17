from django.conf import settings
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from apps.core.models import TenantScopedModel


class ServiceItem(TenantScopedModel):
    """Billable items that aren't already priced in another catalog —
    consultation fees, procedures, misc charges. Pharmacy and lab line
    items are priced from Drug.unit_price / LabTest.price directly, so
    there's one source of truth per item type instead of two catalogs that
    could drift out of sync."""

    class Category(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        PROCEDURE = "procedure", "Procedure"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "name"], name="unique_service_item_per_hospital"),
        ]

    def __str__(self):
        return self.name


class Invoice(TenantScopedModel):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    invoice_number = models.CharField(max_length=20)
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="invoices")
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "invoice_number"], name="unique_invoice_number_per_hospital"),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.patient.full_name}"

    @property
    def total_amount(self):
        result = self.line_items.aggregate(
            total=Sum(
                ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField(max_digits=10, decimal_places=2))
            )
        )["total"]
        return result or 0

    @property
    def amount_paid(self):
        return self.payments.aggregate(total=Sum("amount"))["total"] or 0

    @property
    def amount_due(self):
        return self.total_amount - self.amount_paid


class InvoiceLineItem(TenantScopedModel):
    class ItemType(models.TextChoices):
        CONSULTATION = "consultation", "Consultation"
        PHARMACY = "pharmacy", "Pharmacy"
        LAB = "lab", "Lab"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Traceability back to the source record — blank for a manually-added
    # (OTHER, or fallback CONSULTATION) line with no single source row.
    dispense_record = models.ForeignKey(
        "pharmacy.DispenseRecord", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_line_items"
    )
    lab_order = models.ForeignKey(
        "clinical.LabOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_line_items"
    )
    service_item = models.ForeignKey(
        ServiceItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_line_items"
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description} x{self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Payment(TenantScopedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        INSURANCE = "insurance", "Insurance"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, help_text="Transaction ref / insurance claim number")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_method_display()} {self.amount} — {self.invoice.invoice_number}"
