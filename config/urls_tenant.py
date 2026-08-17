"""Tenant urlconf — active whenever CurrentHospitalMiddleware resolves the
request host to a Hospital. No django.contrib.admin here: platform
administration is only reachable on the bare PLATFORM_DOMAIN."""

from django.urls import include, path

urlpatterns = [
    path("accounts/", include("apps.users.urls")),
    path("patients/", include("apps.patients.urls")),
    path("appointments/", include("apps.appointments.urls")),
    path("clinical/", include("apps.clinical.urls")),
    path("pharmacy/", include("apps.pharmacy.urls")),
    path("lab/", include("apps.lab.urls")),
    path("billing/", include("apps.billing.urls")),
    path("wards/", include("apps.wards.urls")),
    path("", include("apps.dashboard.urls")),
]
