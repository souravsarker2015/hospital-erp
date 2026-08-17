from django.contrib import admin

from apps.wards.models import Admission, Bed, Room, Ward


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0


class BedInline(admin.TabularInline):
    model = Bed
    extra = 0


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ["name", "hospital", "ward_type", "is_active"]
    list_filter = ["hospital", "ward_type", "is_active"]
    inlines = [RoomInline]

    def get_queryset(self, request):
        return Ward.all_hospitals.select_related("hospital")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["room_number", "ward", "hospital"]
    list_filter = ["hospital", "ward"]
    inlines = [BedInline]

    def get_queryset(self, request):
        return Room.all_hospitals.select_related("ward", "hospital")


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ["bed_number", "room", "hospital", "status", "daily_rate"]
    list_filter = ["hospital", "status"]

    def get_queryset(self, request):
        return Bed.all_hospitals.select_related("room", "hospital")


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ["patient", "bed", "hospital", "status", "admission_date", "discharge_date"]
    list_filter = ["hospital", "status"]
    search_fields = ["patient__first_name", "patient__last_name", "patient__mrn"]

    def get_queryset(self, request):
        return Admission.all_hospitals.select_related("patient", "bed", "hospital")
