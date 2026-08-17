from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class LabTest(TenantScopedModel):
    class SampleType(models.TextChoices):
        BLOOD = "blood", "Blood"
        URINE = "urine", "Urine"
        STOOL = "stool", "Stool"
        SPUTUM = "sputum", "Sputum"
        SWAB = "swab", "Swab"
        TISSUE = "tissue", "Tissue"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, blank=True, help_text="Internal test code, e.g. CBC")
    sample_type = models.CharField(max_length=20, choices=SampleType.choices, default=SampleType.BLOOD)
    unit = models.CharField(max_length=50, blank=True, help_text="e.g. mg/dL, x10^9/L")
    reference_range = models.CharField(max_length=100, blank=True, help_text="e.g. 4.5–11.0 x10^9/L")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "name"], name="unique_lab_test_per_hospital"),
        ]

    def __str__(self):
        return self.name


class LabResult(TenantScopedModel):
    class SampleStatus(models.TextChoices):
        PENDING = "pending", "Pending Collection"
        COLLECTED = "collected", "Sample Collected"
        RESULT_ENTERED = "result_entered", "Result Entered"

    lab_order = models.OneToOneField(
        "clinical.LabOrder", on_delete=models.CASCADE, related_name="lab_result"
    )
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT, related_name="results")
    sample_status = models.CharField(max_length=20, choices=SampleStatus.choices, default=SampleStatus.PENDING)
    sample_collected_at = models.DateTimeField(null=True, blank=True)
    sample_collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    result_value = models.CharField(max_length=200, blank=True)
    result_notes = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)
    result_entered_at = models.DateTimeField(null=True, blank=True)
    result_entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"{self.test.name} — {self.lab_order}"

    @property
    def patient(self):
        return self.lab_order.consultation.appointment.patient
