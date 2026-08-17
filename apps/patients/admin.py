from django.contrib import admin

from apps.patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["mrn", "full_name", "hospital", "phone_number", "gender", "blood_group", "is_active"]
    list_filter = ["hospital", "gender", "blood_group", "is_active"]
    search_fields = ["mrn", "first_name", "last_name", "phone_number"]

    def get_queryset(self, request):
        return Patient.all_hospitals.all()
