from datetime import datetime

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from apps.appointments.forms import BookAppointmentForm, DoctorScheduleForm
from apps.appointments.models import Appointment, DoctorSchedule
from apps.appointments.services import (
    OverlappingScheduleError,
    SchedulingError,
    available_slots,
    book_appointment,
    create_schedule,
    transition_status,
)
from apps.core.permissions import RoleRequiredMixin, TenantMemberRequiredMixin
from apps.core.roles import FRONT_DESK_ROLES, QUEUE_MANAGER_ROLES
from apps.patients.models import Patient
from apps.users.models import User


def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return timezone.localdate()


class QueueView(TenantMemberRequiredMixin, TemplateView):
    def get_template_names(self):
        if self.request.htmx:
            return ["appointments/_queue_table.html"]
        return ["appointments/queue.html"]

    def get_context_data(self, **kwargs):
        selected_date = _parse_date(self.request.GET.get("date"))
        doctor_id = self.request.GET.get("doctor", "")

        appointments = (
            Appointment.objects.filter(appointment_date=selected_date)
            .select_related("patient", "doctor")
            .order_by("doctor__first_name", "token_number")
        )
        if doctor_id:
            appointments = appointments.filter(doctor_id=doctor_id)

        return {
            **super().get_context_data(**kwargs),
            "doctors": User.objects.filter(hospital=self.request.hospital, role=User.Role.DOCTOR, is_active=True).order_by("first_name"),
            "appointments": appointments,
            "selected_date": selected_date,
            "selected_doctor": doctor_id,
            "can_manage_queue": self.request.user.role in QUEUE_MANAGER_ROLES,
            "can_book": self.request.user.role in FRONT_DESK_ROLES,
        }


class AppointmentStatusView(RoleRequiredMixin, View):
    allowed_roles = QUEUE_MANAGER_ROLES

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        try:
            transition_status(appointment, request.POST.get("status", ""))
        except SchedulingError:
            pass  # stale double-click on an already-transitioned row; just re-render current state
        return render(request, "appointments/_queue_row.html", {"appointment": appointment, "can_manage_queue": True})


class BookAppointmentView(RoleRequiredMixin, FormView):
    allowed_roles = FRONT_DESK_ROLES
    form_class = BookAppointmentForm
    template_name = "appointments/book.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "hospital": self.request.hospital}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "today": timezone.localdate().isoformat()}

    def form_valid(self, form):
        try:
            appointment = book_appointment(
                hospital=self.request.hospital,
                patient=form.cleaned_data["patient_id"],
                doctor=form.cleaned_data["doctor"],
                appointment_date=form.cleaned_data["appointment_date"],
                start_time=form.cleaned_data["start_time"],
                reason=form.cleaned_data["reason"],
                created_by=self.request.user,
            )
        except SchedulingError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Token #{appointment.token_number} booked for {appointment.patient.full_name} with Dr. {appointment.doctor.get_full_name()}.",
        )
        url = f"{reverse('appointments:queue')}?doctor={appointment.doctor_id}&date={appointment.appointment_date}"
        return redirect(url)


class PatientSearchView(TenantMemberRequiredMixin, View):
    """htmx endpoint backing the booking form's patient picker."""

    def get(self, request):
        q = request.GET.get("q", "").strip()
        results = []
        if q:
            results = Patient.objects.filter(is_active=True).filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone_number__icontains=q) | Q(mrn__icontains=q)
            )[:8]
        return render(request, "appointments/_patient_results.html", {"results": results, "query": q})


class SlotsView(TenantMemberRequiredMixin, View):
    """htmx endpoint backing the booking form's slot picker."""

    def get(self, request):
        doctor_id = request.GET.get("doctor", "")
        appointment_date = _parse_date(request.GET.get("appointment_date"))
        doctor = User.objects.filter(pk=doctor_id, hospital=request.hospital, role=User.Role.DOCTOR).first()
        slots = available_slots(doctor, appointment_date) if doctor else []
        return render(request, "appointments/_slot_picker.html", {"slots": slots, "doctor": doctor})


class DoctorScheduleListView(RoleRequiredMixin, ListView):
    allowed_roles = [User.Role.ADMIN]
    template_name = "appointments/schedule_list.html"
    context_object_name = "schedules"

    def get_queryset(self):
        return DoctorSchedule.objects.filter(is_active=True).select_related("doctor")

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "form": DoctorScheduleForm(hospital=self.request.hospital)}


class DoctorScheduleCreateView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request):
        form = DoctorScheduleForm(request.POST, hospital=request.hospital)
        if form.is_valid():
            try:
                create_schedule(hospital=request.hospital, **form.cleaned_data)
                return redirect("appointments:schedules")
            except OverlappingScheduleError as exc:
                form.add_error(None, str(exc))
        schedules = DoctorSchedule.objects.filter(is_active=True).select_related("doctor")
        return render(request, "appointments/schedule_list.html", {"schedules": schedules, "form": form})


class DoctorScheduleDeleteView(RoleRequiredMixin, View):
    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk):
        get_object_or_404(DoctorSchedule, pk=pk).delete()
        return HttpResponse("")
