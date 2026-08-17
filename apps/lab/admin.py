from django.contrib import admin

from apps.lab.models import LabResult, LabTest


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "hospital", "sample_type", "is_active"]
    list_filter = ["hospital", "sample_type", "is_active"]
    search_fields = ["name", "code"]

    def get_queryset(self, request):
        return LabTest.all_hospitals.select_related("hospital")


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ["test", "hospital", "sample_status", "is_abnormal", "result_entered_at"]
    list_filter = ["hospital", "sample_status", "is_abnormal"]

    def get_queryset(self, request):
        return LabResult.all_hospitals.select_related("test", "hospital")
