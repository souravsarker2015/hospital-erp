"""Sidebar nav for the tenant app (templates/base_tenant.html). url_name=None
means the module isn't built yet — it renders as a disabled 'Coming soon'
item instead of a link, so the sidebar shows the full product shape without
ever pointing at a URL that doesn't exist yet."""

TENANT_NAV_ITEMS = [
    {"label": "Dashboard", "icon": "layout-dashboard", "namespace": "dashboard", "url_name": "dashboard:home"},
    {"label": "Patients", "icon": "users-round", "namespace": "patients", "url_name": "patients:list"},
    {"label": "Appointments", "icon": "calendar-clock", "namespace": "appointments", "url_name": "appointments:queue"},
    {"label": "Clinical", "icon": "stethoscope", "namespace": "clinical", "url_name": None},
    {"label": "Pharmacy", "icon": "pill", "namespace": "pharmacy", "url_name": "pharmacy:drug_list"},
    {"label": "Lab", "icon": "flask-conical", "namespace": "lab", "url_name": "lab:test_list"},
    {"label": "Billing", "icon": "receipt", "namespace": "billing", "url_name": "billing:invoice_list"},
    {"label": "Wards", "icon": "bed-double", "namespace": "wards", "url_name": None},
]
