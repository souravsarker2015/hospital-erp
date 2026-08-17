from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class Vitals(TenantScopedModel):
    appointment = models.OneToOneField("appointments.Appointment", on_delete=models.CASCADE, related_name="vitals")
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    blood_pressure_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    pulse_rate = models.PositiveSmallIntegerField(null=True, blank=True, help_text="beats per minute")
    respiratory_rate = models.PositiveSmallIntegerField(null=True, blank=True, help_text="breaths per minute")
    spo2_percent = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Oxygen saturation %")
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    def __str__(self):
        return f"Vitals for {self.appointment}"

    @property
    def bmi(self):
        if not (self.weight_kg and self.height_cm):
            return None
        height_m = float(self.height_cm) / 100
        return round(float(self.weight_kg) / (height_m**2), 1)


class Consultation(TenantScopedModel):
    appointment = models.OneToOneField("appointments.Appointment", on_delete=models.CASCADE, related_name="consultation")
    chief_complaint = models.CharField(max_length=255, blank=True)
    history_notes = models.TextField(blank=True)
    examination_notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    icd10_code = models.CharField(max_length=10, blank=True, verbose_name="ICD-10 code")
    advice = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Consultation for {self.appointment}"

    @property
    def patient(self):
        return self.appointment.patient

    @property
    def doctor(self):
        return self.appointment.doctor


class PrescriptionItem(TenantScopedModel):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="prescription_items")
    drug_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, blank=True, help_text="e.g. 500mg")
    frequency = models.CharField(max_length=100, blank=True, help_text="e.g. 1-0-1 (morning-noon-night)")
    duration = models.CharField(max_length=100, blank=True, help_text="e.g. 5 days")
    instructions = models.CharField(max_length=255, blank=True, help_text="e.g. after meals")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.drug_name} ({self.dosage})"


class LabOrder(TenantScopedModel):
    class Status(models.TextChoices):
        ORDERED = "ordered", "Ordered"
        CANCELLED = "cancelled", "Cancelled"
        # Sample-collected/result-entry states are added when Phase 5 builds
        # the full Lab module — this just records what a doctor ordered.

    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="lab_orders")
    test_name = models.CharField(max_length=200)
    notes = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.test_name
