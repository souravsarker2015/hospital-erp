from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        DOCTOR = "doctor", "Doctor"
        NURSE = "nurse", "Nurse"
        RECEPTIONIST = "receptionist", "Receptionist"
        PHARMACIST = "pharmacist", "Pharmacist"
        LAB_TECHNICIAN = "lab_technician", "Lab Technician"
        ACCOUNTANT = "accountant", "Accountant"
        # Reserved for the patient-portal phase; no views use this yet.
        PATIENT = "patient", "Patient"

    # Nullable only for platform superusers (createsuperuser, platform admin
    # staff) who manage the tenants themselves rather than belonging to one.
    # Every hospital-side user gets a hospital at signup/creation time.
    hospital = models.ForeignKey(
        "tenants.Hospital",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="users",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTIONIST)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.get_username()

    @property
    def is_hospital_admin(self) -> bool:
        return self.role == self.Role.ADMIN
