"""Role-based dashboard: real queries against every module that's shipped
(Patients through Wards), plus Chart.js data for the richer roles. Replaces
the Phase 0.5 static "—" placeholders now that there's real data to show."""

from datetime import timedelta

from django.db.models import Count, Sum
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.billing.models import Invoice, Payment
from apps.clinical.models import LabOrder, PrescriptionItem
from apps.patients.models import Patient
from apps.pharmacy.services import get_alert_counts as pharmacy_alert_counts
from apps.users.models import User
from apps.wards.models import Admission, Bed

_ACTIVE_APPOINTMENT_STATUSES = [
    Appointment.Status.SCHEDULED,
    Appointment.Status.CHECKED_IN,
    Appointment.Status.IN_CONSULTATION,
]


def _pending_lab_orders(**filters):
    return (
        LabOrder.objects.exclude(status=LabOrder.Status.CANCELLED)
        .exclude(lab_result__sample_status="result_entered")
        .filter(**filters)
        .count()
    )


def _admin_widgets(hospital, user, today):
    revenue_today = Payment.objects.filter(created_at__date=today).aggregate(total=Sum("amount"))["total"] or 0
    total_beds = Bed.objects.count()
    occupied_beds = Bed.objects.filter(status=Bed.Status.OCCUPIED).count()
    low_stock_count, _expiring_count = pharmacy_alert_counts(hospital)
    active_staff = User.objects.filter(hospital=hospital, is_active=True).exclude(role=User.Role.PATIENT).count()

    return [
        {
            "title": "Today's Appointments",
            "icon": "calendar-clock",
            "value": Appointment.objects.filter(appointment_date=today).exclude(status=Appointment.Status.CANCELLED).count(),
            "href": f"{reverse('appointments:queue')}?date={today}",
        },
        {"title": "Today's Revenue", "icon": "receipt", "value": f"${revenue_today}", "href": reverse("billing:invoice_list")},
        {"title": "Bed Occupancy", "icon": "bed-double", "value": f"{occupied_beds}/{total_beds}", "href": reverse("wards:board")},
        {
            "title": "Low Stock Items",
            "icon": "pill",
            "value": low_stock_count,
            "href": f"{reverse('pharmacy:drug_list')}?filter=low_stock",
        },
        {"title": "Pending Lab Results", "icon": "flask-conical", "value": _pending_lab_orders(), "href": reverse("lab:queue")},
        {"title": "Active Staff", "icon": "users-round", "value": active_staff},
    ]


def _doctor_widgets(hospital, user, today):
    my_appointments_today = Appointment.objects.filter(doctor=user, appointment_date=today)
    return [
        {
            "title": "My Queue Today",
            "icon": "calendar-clock",
            "value": my_appointments_today.filter(status__in=_ACTIVE_APPOINTMENT_STATUSES).count(),
            "href": f"{reverse('appointments:queue')}?date={today}&doctor={user.pk}",
        },
        {
            "title": "Patients Seen Today",
            "icon": "users-round",
            "value": my_appointments_today.filter(status=Appointment.Status.COMPLETED).count(),
        },
        {
            "title": "Pending Lab Results",
            "icon": "flask-conical",
            "value": _pending_lab_orders(consultation__appointment__doctor=user),
            "href": reverse("lab:queue"),
        },
    ]


def _nurse_widgets(hospital, user, today):
    vitals_pending = Appointment.objects.filter(
        appointment_date=today,
        status__in=[Appointment.Status.CHECKED_IN, Appointment.Status.IN_CONSULTATION],
        vitals__isnull=True,
    ).count()
    total_beds = Bed.objects.count()
    occupied_beds = Bed.objects.filter(status=Bed.Status.OCCUPIED).count()

    return [
        {
            "title": "Vitals Pending",
            "icon": "activity",
            "value": vitals_pending,
            "href": f"{reverse('appointments:queue')}?date={today}",
        },
        {
            "title": "Today's Admissions",
            "icon": "bed-double",
            "value": Admission.objects.filter(admission_date__date=today).count(),
            "href": reverse("wards:board"),
        },
        {"title": "Ward Occupancy", "icon": "layout-dashboard", "value": f"{occupied_beds}/{total_beds}", "href": reverse("wards:board")},
    ]


def _receptionist_widgets(hospital, user, today):
    today_appointments = Appointment.objects.filter(appointment_date=today)
    return [
        {
            "title": "Today's OPD Queue",
            "icon": "calendar-clock",
            "value": today_appointments.filter(status__in=_ACTIVE_APPOINTMENT_STATUSES).count(),
            "href": f"{reverse('appointments:queue')}?date={today}",
        },
        {
            "title": "New Registrations Today",
            "icon": "users-round",
            "value": Patient.objects.filter(created_at__date=today).count(),
            "href": reverse("patients:list"),
        },
        {
            "title": "Awaiting Check-in",
            "icon": "clock",
            "value": today_appointments.filter(status=Appointment.Status.SCHEDULED).count(),
            "href": f"{reverse('appointments:queue')}?date={today}",
        },
    ]


def _pharmacist_widgets(hospital, user, today):
    low_stock_count, expiring_count = pharmacy_alert_counts(hospital)
    pending_dispense = PrescriptionItem.objects.filter(
        consultation__appointment__status=Appointment.Status.COMPLETED, dispense_record__isnull=True
    ).count()

    return [
        {
            "title": "Low Stock Items",
            "icon": "pill",
            "value": low_stock_count,
            "href": f"{reverse('pharmacy:drug_list')}?filter=low_stock",
        },
        {"title": "Prescriptions to Dispense", "icon": "clipboard-list", "value": pending_dispense, "href": reverse("pharmacy:dispense_queue")},
        {
            "title": "Batches Expiring Soon",
            "icon": "flask-conical",
            "value": expiring_count,
            "href": f"{reverse('pharmacy:drug_list')}?filter=expiring",
        },
    ]


def _lab_technician_widgets(hospital, user, today):
    pending_collection = LabOrder.objects.exclude(status=LabOrder.Status.CANCELLED).filter(lab_result__isnull=True).count()
    results_to_enter = LabOrder.objects.filter(lab_result__sample_status="collected").count()

    return [
        {
            "title": "Pending Sample Collections",
            "icon": "flask-conical",
            "value": pending_collection,
            "href": f"{reverse('lab:queue')}?status=pending",
        },
        {
            "title": "Results to Enter",
            "icon": "clipboard-list",
            "value": results_to_enter,
            "href": f"{reverse('lab:queue')}?status=collected",
        },
    ]


def _accountant_widgets(hospital, user, today):
    revenue_today = Payment.objects.filter(created_at__date=today).aggregate(total=Sum("amount"))["total"] or 0
    unpaid = Invoice.objects.exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED])
    pending_dues = sum((invoice.amount_due for invoice in unpaid), start=0)

    return [
        {"title": "Today's Revenue", "icon": "receipt", "value": f"${revenue_today}", "href": reverse("billing:invoice_list")},
        {
            "title": "Pending Dues",
            "icon": "clock",
            "value": f"${pending_dues}",
            "href": f"{reverse('billing:invoice_list')}?status=unpaid",
        },
        {
            "title": "Invoices Issued Today",
            "icon": "clipboard-list",
            "value": Invoice.objects.filter(created_at__date=today).count(),
            "href": reverse("billing:invoice_list"),
        },
    ]


_WIDGET_BUILDERS = {
    User.Role.ADMIN: _admin_widgets,
    User.Role.DOCTOR: _doctor_widgets,
    User.Role.NURSE: _nurse_widgets,
    User.Role.RECEPTIONIST: _receptionist_widgets,
    User.Role.PHARMACIST: _pharmacist_widgets,
    User.Role.LAB_TECHNICIAN: _lab_technician_widgets,
    User.Role.ACCOUNTANT: _accountant_widgets,
    User.Role.PATIENT: lambda hospital, user, today: [],
}


def widgets_for_user(hospital, user) -> list[dict]:
    builder = _WIDGET_BUILDERS.get(user.role)
    if builder is None:
        return []
    return builder(hospital, user, timezone.localdate())


def revenue_last_7_days_chart() -> dict:
    today = timezone.localdate()
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    totals = []
    for day in days:
        total = Payment.objects.filter(created_at__date=day).aggregate(total=Sum("amount"))["total"] or 0
        totals.append(float(total))
    return {"labels": [day.strftime("%a") for day in days], "data": totals}


def bed_occupancy_chart() -> dict | None:
    if not Bed.objects.exists():
        return None
    occupied = Bed.objects.filter(status=Bed.Status.OCCUPIED).count()
    available = Bed.objects.filter(status=Bed.Status.AVAILABLE).count()
    maintenance = Bed.objects.filter(status=Bed.Status.MAINTENANCE).count()
    return {"labels": ["Occupied", "Available", "Maintenance"], "data": [occupied, available, maintenance]}


def appointment_status_chart(today, doctor=None) -> dict:
    qs = Appointment.objects.filter(appointment_date=today)
    if doctor is not None:
        qs = qs.filter(doctor=doctor)
    counts = dict.fromkeys(Appointment.Status.values, 0)
    for row in qs.values("status").annotate(n=Count("id")):
        counts[row["status"]] = row["n"]
    return {
        "labels": [label for _value, label in Appointment.Status.choices],
        "data": [counts[value] for value, _label in Appointment.Status.choices],
    }
