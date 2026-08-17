import logging

from django.db import transaction

from apps.appointments.models import Appointment
from apps.appointments.services import transition_status
from apps.clinical.models import Consultation
from apps.core.logging_utils import log_context

logger = logging.getLogger("clinical")


def get_or_start_consultation(appointment: Appointment, user) -> Consultation:
    consultation, created = Consultation.objects.get_or_create(
        hospital=appointment.hospital,
        appointment=appointment,
        defaults={"created_by": user},
    )
    if created:
        logger.info(
            "consultation.started",
            extra=log_context(hospital_id=appointment.hospital_id, user_id=user.id),
        )
    if appointment.status == Appointment.Status.CHECKED_IN:
        transition_status(appointment, Appointment.Status.IN_CONSULTATION)
    return consultation


@transaction.atomic
def complete_consultation(consultation: Consultation, appointment: Appointment) -> Consultation:
    transition_status(appointment, Appointment.Status.COMPLETED)
    logger.info(
        "consultation.completed",
        extra=log_context(hospital_id=appointment.hospital_id, user_id=appointment.doctor_id),
    )
    return consultation
