from django.contrib import admin

from apps.billing.models import Invoice, InvoiceLineItem, Payment, ServiceItem


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ["name", "hospital", "category", "price", "is_active"]
    list_filter = ["hospital", "category", "is_active"]

    def get_queryset(self, request):
        return ServiceItem.all_hospitals.select_related("hospital")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "patient", "hospital", "status", "created_at"]
    list_filter = ["hospital", "status"]
    search_fields = ["invoice_number", "patient__first_name", "patient__last_name", "patient__mrn"]
    inlines = [InvoiceLineItemInline, PaymentInline]

    def get_queryset(self, request):
        return Invoice.all_hospitals.select_related("patient", "hospital")
