from django.contrib import admin

from apps.appointments.models import Appointment, DoctorSchedule


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ["doctor", "hospital", "weekday", "start_time", "end_time", "slot_duration_minutes", "is_active"]
    list_filter = ["hospital", "weekday", "is_active"]

    def get_queryset(self, request):
        return DoctorSchedule.all_hospitals.all()


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["token_number", "patient", "doctor", "hospital", "appointment_date", "start_time", "status"]
    list_filter = ["hospital", "status", "appointment_date"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__mrn"]

    def get_queryset(self, request):
        return Appointment.all_hospitals.select_related("patient", "doctor", "hospital")
