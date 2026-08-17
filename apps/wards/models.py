from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TenantScopedModel


class Ward(TenantScopedModel):
    class WardType(models.TextChoices):
        GENERAL = "general", "General"
        ICU = "icu", "ICU"
        MATERNITY = "maternity", "Maternity"
        PEDIATRIC = "pediatric", "Pediatric"
        SURGICAL = "surgical", "Surgical"
        EMERGENCY = "emergency", "Emergency"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=20, choices=WardType.choices, default=WardType.GENERAL)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "name"], name="unique_ward_per_hospital"),
        ]

    def __str__(self):
        return self.name


class Room(TenantScopedModel):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=20)

    class Meta:
        ordering = ["room_number"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "ward", "room_number"], name="unique_room_per_ward"),
        ]

    def __str__(self):
        return f"{self.ward.name} — Room {self.room_number}"


class Bed(TenantScopedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        MAINTENANCE = "maintenance", "Maintenance"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    bed_number = models.CharField(max_length=20)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        ordering = ["bed_number"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "room", "bed_number"], name="unique_bed_per_room"),
        ]

    def __str__(self):
        return f"{self.room} — Bed {self.bed_number}"

    @property
    def ward(self):
        return self.room.ward

    @property
    def current_admission(self):
        return self.admissions.filter(status=Admission.Status.ADMITTED).first()


class Admission(TenantScopedModel):
    class Status(models.TextChoices):
        ADMITTED = "admitted", "Admitted"
        DISCHARGED = "discharged", "Discharged"

    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="admissions")
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="admissions")
    admitting_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="admissions_as_doctor",
        limit_choices_to={"role": "doctor"},
    )
    reason = models.CharField(max_length=255)
    admission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ADMITTED)
    discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_summary = models.TextField(blank=True)
    discharged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-admission_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["bed"],
                condition=models.Q(status="admitted"),
                name="one_active_admission_per_bed",
            ),
        ]

    def __str__(self):
        return f"{self.patient.full_name} — {self.bed}"

    @property
    def nights_stayed(self) -> int:
        end = self.discharge_date or timezone.now()
        return max((end - self.admission_date).days, 0)
