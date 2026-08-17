from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.appointments.models import Appointment
from apps.clinical.forms import ConsultationForm, LabOrderFormSet, PrescriptionItemFormSet, VitalsForm
from apps.clinical.models import Consultation, Vitals
from apps.clinical.services import complete_consultation, get_or_start_consultation
from apps.core.permissions import role_required
from apps.core.roles import ALL_STAFF_ROLES, CLINICAL_ROLES, VITALS_ROLES

CONSULTABLE_STATUSES = {
    Appointment.Status.CHECKED_IN,
    Appointment.Status.IN_CONSULTATION,
    Appointment.Status.COMPLETED,
}


@role_required(*VITALS_ROLES)
def vitals_view(request, appointment_pk):
    appointment = get_object_or_404(Appointment, pk=appointment_pk)
    try:
        instance = appointment.vitals
    except Vitals.DoesNotExist:
        instance = None

    if request.method == "POST":
        form = VitalsForm(request.POST, instance=instance)
        if form.is_valid():
            vitals = form.save(commit=False)
            vitals.hospital = appointment.hospital
            vitals.appointment = appointment
            vitals.recorded_by = request.user
            vitals.save()
            messages.success(request, "Vitals recorded.")
            return redirect("appointments:queue")
    else:
        form = VitalsForm(instance=instance)

    return render(request, "clinical/vitals_form.html", {"form": form, "appointment": appointment})


@role_required(*CLINICAL_ROLES)
def consultation_view(request, appointment_pk):
    appointment = get_object_or_404(Appointment, pk=appointment_pk)
    if appointment.status not in CONSULTABLE_STATUSES:
        messages.error(request, "This patient must be checked in before starting a consultation.")
        return redirect("appointments:queue")

    consultation = get_or_start_consultation(appointment, request.user)
    is_locked = appointment.status == Appointment.Status.COMPLETED

    if request.method == "POST" and not is_locked:
        form = ConsultationForm(request.POST, instance=consultation)
        prescription_formset = PrescriptionItemFormSet(request.POST, instance=consultation, prefix="rx")
        lab_formset = LabOrderFormSet(request.POST, instance=consultation, prefix="lab")

        if form.is_valid() and prescription_formset.is_valid() and lab_formset.is_valid():
            with transaction.atomic():
                form.save()

                items = prescription_formset.save(commit=False)
                for item in items:
                    item.hospital = appointment.hospital
                    item.consultation = consultation
                    item.save()
                for obj in prescription_formset.deleted_objects:
                    obj.delete()

                orders = lab_formset.save(commit=False)
                for order in orders:
                    order.hospital = appointment.hospital
                    order.consultation = consultation
                    order.save()
                for obj in lab_formset.deleted_objects:
                    obj.delete()

                if request.POST.get("action") == "complete":
                    complete_consultation(consultation, appointment)
                    messages.success(request, "Consultation completed.")
                    return redirect("appointments:queue")

            messages.success(request, "Consultation saved.")
            return redirect("clinical:consultation", appointment_pk=appointment.pk)
    else:
        form = ConsultationForm(instance=consultation)
        prescription_formset = PrescriptionItemFormSet(instance=consultation, prefix="rx")
        lab_formset = LabOrderFormSet(instance=consultation, prefix="lab")

    try:
        vitals = appointment.vitals
    except Vitals.DoesNotExist:
        vitals = None

    return render(
        request,
        "clinical/consultation.html",
        {
            "appointment": appointment,
            "patient": appointment.patient,
            "consultation": consultation,
            "vitals": vitals,
            "form": form,
            "prescription_formset": prescription_formset,
            "lab_formset": lab_formset,
            "is_locked": is_locked,
        },
    )


@role_required(*ALL_STAFF_ROLES)
def prescription_print_view(request, appointment_pk):
    appointment = get_object_or_404(Appointment, pk=appointment_pk)
    consultation = get_object_or_404(Consultation, appointment=appointment)
    return render(
        request,
        "clinical/prescription_print.html",
        {
            "appointment": appointment,
            "patient": appointment.patient,
            "consultation": consultation,
            "prescription_items": consultation.prescription_items.all(),
        },
    )
