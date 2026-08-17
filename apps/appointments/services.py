import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Max

from apps.appointments.models import Appointment, DoctorSchedule
from apps.core.logging_utils import log_context
from apps.users.models import User

logger = logging.getLogger("appointments")

VALID_TRANSITIONS = {
    Appointment.Status.SCHEDULED: {Appointment.Status.CHECKED_IN, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW},
    Appointment.Status.CHECKED_IN: {Appointment.Status.IN_CONSULTATION, Appointment.Status.CANCELLED},
    Appointment.Status.IN_CONSULTATION: {Appointment.Status.COMPLETED},
    Appointment.Status.COMPLETED: set(),
    Appointment.Status.CANCELLED: set(),
    Appointment.Status.NO_SHOW: set(),
}


class SchedulingError(Exception):
    pass


class OutsideScheduleError(SchedulingError):
    pass


class SlotTakenError(SchedulingError):
    pass


class InvalidTransitionError(SchedulingError):
    pass


class OverlappingScheduleError(SchedulingError):
    pass


def available_slots(doctor, appointment_date) -> list:
    """Every bookable start_time for this doctor on this date: generated
    from their weekday schedule blocks, minus times already booked."""
    schedules = DoctorSchedule.objects.filter(
        doctor=doctor, weekday=appointment_date.weekday(), is_active=True
    )
    booked = set(
        Appointment.objects.filter(doctor=doctor, appointment_date=appointment_date)
        .exclude(status=Appointment.Status.CANCELLED)
        .values_list("start_time", flat=True)
    )
    slots = []
    for schedule in schedules:
        current = datetime.combine(appointment_date, schedule.start_time)
        end = datetime.combine(appointment_date, schedule.end_time)
        step = timedelta(minutes=schedule.slot_duration_minutes)
        while current + step <= end:
            slot_time = current.time()
            if slot_time not in booked:
                slots.append(slot_time)
            current += step
    return sorted(slots)


@transaction.atomic
def book_appointment(*, hospital, patient, doctor, appointment_date, start_time, reason="", created_by=None) -> Appointment:
    # Locking the doctor row serializes token assignment for concurrent
    # bookings the same way apps.patients.services locks the Hospital row
    # for MRN assignment — there's no other row guaranteed to already exist
    # for this doctor+date to lock on instead.
    locked_doctor = User.objects.select_for_update().get(pk=doctor.pk)

    schedule = DoctorSchedule.objects.filter(
        doctor=locked_doctor,
        weekday=appointment_date.weekday(),
        is_active=True,
        start_time__lte=start_time,
        end_time__gt=start_time,
    ).first()
    if schedule is None:
        raise OutsideScheduleError("That time is outside the doctor's schedule.")

    slot_taken = (
        Appointment.objects.filter(doctor=locked_doctor, appointment_date=appointment_date, start_time=start_time)
        .exclude(status=Appointment.Status.CANCELLED)
        .exists()
    )
    if slot_taken:
        raise SlotTakenError("That slot was just booked. Please pick another.")

    last_token = (
        Appointment.objects.filter(hospital=hospital, doctor=locked_doctor, appointment_date=appointment_date)
        .aggregate(Max("token_number"))["token_number__max"]
        or 0
    )
    end_time = (datetime.combine(appointment_date, start_time) + timedelta(minutes=schedule.slot_duration_minutes)).time()

    appointment = Appointment.objects.create(
        hospital=hospital,
        patient=patient,
        doctor=locked_doctor,
        appointment_date=appointment_date,
        start_time=start_time,
        end_time=end_time,
        token_number=last_token + 1,
        reason=reason,
        created_by=created_by,
    )
    logger.info(
        "appointment.booked",
        extra=log_context(hospital_id=hospital.id, user_id=getattr(created_by, "id", None), token=appointment.token_number),
    )
    return appointment


def transition_status(appointment: Appointment, new_status: str) -> Appointment:
    allowed = VALID_TRANSITIONS.get(appointment.status, set())
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Can't move an appointment from {appointment.get_status_display()} to {new_status}."
        )
    appointment.status = new_status
    appointment.save(update_fields=["status", "updated_at"])
    logger.info(
        "appointment.status_changed",
        extra=log_context(hospital_id=appointment.hospital_id, status=new_status, token=appointment.token_number),
    )
    return appointment


def create_schedule(*, hospital, doctor, weekday, start_time, end_time, slot_duration_minutes) -> DoctorSchedule:
    overlapping = DoctorSchedule.objects.filter(
        doctor=doctor, weekday=weekday, start_time__lt=end_time, end_time__gt=start_time
    ).exists()
    if overlapping:
        raise OverlappingScheduleError("This overlaps an existing schedule block for this doctor.")
    return DoctorSchedule.objects.create(
        hospital=hospital,
        doctor=doctor,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        slot_duration_minutes=slot_duration_minutes,
    )
