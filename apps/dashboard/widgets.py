"""Role-based dashboard widget shell. Values are "—" everywhere on purpose:
no clinical/appointment/pharmacy models exist yet (Phase 1+ builds those),
so these are honest zero-state placeholders, not fabricated numbers. Swap
the "value" callables for real querysets as each phase lands."""

from apps.users.models import User

ROLE_WIDGETS = {
    User.Role.ADMIN: [
        {"title": "Today's Appointments", "icon": "calendar-clock"},
        {"title": "Today's Revenue", "icon": "receipt"},
        {"title": "Bed Occupancy", "icon": "bed-double"},
        {"title": "Low Stock Items", "icon": "pill"},
        {"title": "Pending Lab Results", "icon": "flask-conical"},
        {"title": "Active Staff", "icon": "users-round"},
    ],
    User.Role.DOCTOR: [
        {"title": "My Queue Today", "icon": "calendar-clock"},
        {"title": "Patients Seen Today", "icon": "users-round"},
        {"title": "Pending Lab Results", "icon": "flask-conical"},
    ],
    User.Role.NURSE: [
        {"title": "Vitals Pending", "icon": "activity"},
        {"title": "Today's Admissions", "icon": "bed-double"},
        {"title": "Ward Occupancy", "icon": "layout-dashboard"},
    ],
    User.Role.RECEPTIONIST: [
        {"title": "Today's OPD Queue", "icon": "calendar-clock"},
        {"title": "New Registrations Today", "icon": "users-round"},
        {"title": "Awaiting Check-in", "icon": "clock"},
    ],
    User.Role.PHARMACIST: [
        {"title": "Low Stock Items", "icon": "pill"},
        {"title": "Prescriptions to Dispense", "icon": "clipboard-list"},
        {"title": "Batches Expiring Soon", "icon": "flask-conical"},
    ],
    User.Role.LAB_TECHNICIAN: [
        {"title": "Pending Sample Collections", "icon": "flask-conical"},
        {"title": "Results to Enter", "icon": "clipboard-list"},
    ],
    User.Role.ACCOUNTANT: [
        {"title": "Today's Revenue", "icon": "receipt"},
        {"title": "Pending Dues", "icon": "clock"},
        {"title": "Invoices Issued Today", "icon": "clipboard-list"},
    ],
    User.Role.PATIENT: [],
}


def widgets_for_role(role: str) -> list[dict]:
    return ROLE_WIDGETS.get(role, [])
