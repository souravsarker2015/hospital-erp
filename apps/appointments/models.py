from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantScopedModel


class DoctorSchedule(TenantScopedModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="schedules",
        limit_choices_to={"role": "doctor"},
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration_minutes = models.PositiveSmallIntegerField(default=15)

    class Meta:
        ordering = ["doctor__first_name", "weekday", "start_time"]
        indexes = [models.Index(fields=["hospital", "doctor", "weekday"])]

    def __str__(self):
        return f"{self.doctor.get_full_name()} — {self.get_weekday_display()} {self.start_time}–{self.end_time}"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")


class Appointment(TenantScopedModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CHECKED_IN = "checked_in", "Checked in"
        IN_CONSULTATION = "in_consultation", "In consultation"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
        limit_choices_to={"role": "doctor"},
    )
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    token_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["appointment_date", "token_number"]
        constraints = [
            # Backstop against double-booking the same slot — condition
            # excludes cancelled appointments so a freed slot can be rebooked.
            models.UniqueConstraint(
                fields=["hospital", "doctor", "appointment_date", "start_time"],
                condition=~models.Q(status="cancelled"),
                name="unique_doctor_slot_per_day",
            ),
            models.UniqueConstraint(
                fields=["hospital", "doctor", "appointment_date", "token_number"],
                name="unique_token_per_doctor_per_day",
            ),
        ]
        indexes = [models.Index(fields=["hospital", "doctor", "appointment_date"])]

    def __str__(self):
        return f"Token {self.token_number} — {self.patient.full_name} with {self.doctor.get_full_name()}"
