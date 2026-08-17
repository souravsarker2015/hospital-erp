from django.contrib import admin

from apps.pharmacy.models import DispenseRecord, Drug, StockBatch, StockMovement


class StockBatchInline(admin.TabularInline):
    model = StockBatch
    extra = 0


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ["name", "strength", "hospital", "unit", "low_stock_threshold", "is_active"]
    list_filter = ["hospital", "unit", "is_active"]
    search_fields = ["name", "generic_name"]
    inlines = [StockBatchInline]

    def get_queryset(self, request):
        return Drug.all_hospitals.select_related("hospital")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["drug", "hospital", "movement_type", "quantity", "performed_by", "created_at"]
    list_filter = ["hospital", "movement_type"]

    def get_queryset(self, request):
        return StockMovement.all_hospitals.select_related("drug", "hospital", "performed_by")


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    list_display = ["drug", "hospital", "quantity", "dispensed_by", "created_at"]
    list_filter = ["hospital"]

    def get_queryset(self, request):
        return DispenseRecord.all_hospitals.select_related("drug", "hospital", "dispensed_by")
