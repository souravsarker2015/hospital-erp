from django.contrib import admin

from apps.clinical.models import Consultation, LabOrder, PrescriptionItem, Vitals


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


class LabOrderInline(admin.TabularInline):
    model = LabOrder
    extra = 0


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ["appointment", "hospital", "icd10_code", "created_at"]
    list_filter = ["hospital"]
    inlines = [PrescriptionItemInline, LabOrderInline]

    def get_queryset(self, request):
        return Consultation.all_hospitals.select_related("appointment", "hospital")


@admin.register(Vitals)
class VitalsAdmin(admin.ModelAdmin):
    list_display = ["appointment", "hospital", "pulse_rate", "spo2_percent", "recorded_by"]
    list_filter = ["hospital"]

    def get_queryset(self, request):
        return Vitals.all_hospitals.select_related("appointment", "hospital")
