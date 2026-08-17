import logging

from django.db import transaction

from apps.core.logging_utils import log_context
from apps.patients.models import Patient
from apps.tenants.models import Hospital

logger = logging.getLogger("patients")


def _next_mrn(hospital: Hospital) -> str:
    """Locks the hospital row so two concurrent registrations can't be
    handed the same number — the shared-schema equivalent of a per-tenant
    Postgres sequence, which isn't available here."""
    locked_hospital = Hospital.objects.select_for_update().get(pk=hospital.pk)
    locked_hospital.last_mrn_number += 1
    locked_hospital.save(update_fields=["last_mrn_number"])
    prefix = (locked_hospital.subdomain[:3] or "PT").upper()
    return f"{prefix}-{locked_hospital.last_mrn_number:06d}"


@transaction.atomic
def register_patient(*, hospital: Hospital, created_by=None, **fields) -> Patient:
    mrn = _next_mrn(hospital)
    patient = Patient.objects.create(hospital=hospital, mrn=mrn, created_by=created_by, **fields)
    logger.info(
        "patient.registered",
        extra=log_context(hospital_id=hospital.id, user_id=getattr(created_by, "id", None), mrn=mrn),
    )
    return patient
