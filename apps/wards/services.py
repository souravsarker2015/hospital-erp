import logging

from django.db import transaction
from django.utils import timezone

from apps.core.logging_utils import log_context
from apps.wards.models import Admission, Bed

logger = logging.getLogger("wards")


class WardError(Exception):
    pass


class BedNotAvailableError(WardError):
    pass


class AlreadyDischargedError(WardError):
    pass


@transaction.atomic
def admit_patient(*, hospital, patient, bed: Bed, admitting_doctor, reason: str, created_by=None) -> Admission:
    locked_bed = Bed.objects.select_for_update().get(pk=bed.pk)
    if locked_bed.status != Bed.Status.AVAILABLE:
        raise BedNotAvailableError(f"Bed {locked_bed.bed_number} is not available.")

    admission = Admission.objects.create(
        hospital=hospital,
        patient=patient,
        bed=locked_bed,
        admitting_doctor=admitting_doctor,
        reason=reason,
        created_by=created_by,
    )
    locked_bed.status = Bed.Status.OCCUPIED
    locked_bed.save(update_fields=["status", "updated_at"])
    logger.info(
        "wards.admitted",
        extra=log_context(hospital_id=hospital.id, user_id=getattr(created_by, "id", None), bed=locked_bed.bed_number),
    )
    return admission


@transaction.atomic
def discharge_patient(*, admission: Admission, discharge_summary: str, discharged_by=None) -> Admission:
    if admission.status == Admission.Status.DISCHARGED:
        raise AlreadyDischargedError("This patient has already been discharged.")

    admission.status = Admission.Status.DISCHARGED
    admission.discharge_date = timezone.now()
    admission.discharge_summary = discharge_summary
    admission.discharged_by = discharged_by
    admission.save(update_fields=["status", "discharge_date", "discharge_summary", "discharged_by", "updated_at"])

    locked_bed = Bed.objects.select_for_update().get(pk=admission.bed_id)
    locked_bed.status = Bed.Status.AVAILABLE
    locked_bed.save(update_fields=["status", "updated_at"])

    logger.info(
        "wards.discharged",
        extra=log_context(hospital_id=admission.hospital_id, user_id=getattr(discharged_by, "id", None), bed=locked_bed.bed_number),
    )
    return admission
