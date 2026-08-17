from django.urls import path

from apps.clinical import views

app_name = "clinical"

urlpatterns = [
    path("<uuid:appointment_pk>/vitals/", views.vitals_view, name="vitals"),
    path("<uuid:appointment_pk>/prescription/print/", views.prescription_print_view, name="prescription_print"),
    path("<uuid:appointment_pk>/", views.consultation_view, name="consultation"),
]
