from django.contrib import admin

from apps.tenants.models import Hospital, Plan, Subscription, TenantInvoice
from apps.tenants.services import activate_hospital, suspend_hospital


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_monthly", "includes_pharmacy", "includes_lab", "includes_wards", "is_active"]
    list_editable = ["is_active"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ["name", "subdomain", "plan", "subscription_status", "is_active", "created_at"]
    list_filter = ["subscription_status", "plan", "is_active"]
    search_fields = ["name", "subdomain", "contact_email"]
    actions = ["suspend_hospitals", "activate_hospitals"]

    @admin.action(description="Suspend selected hospitals")
    def suspend_hospitals(self, request, queryset):
        for hospital in queryset:
            suspend_hospital(hospital)

    @admin.action(description="Activate selected hospitals")
    def activate_hospitals(self, request, queryset):
        for hospital in queryset:
            activate_hospital(hospital)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["hospital", "plan", "status", "trial_ends_at", "current_period_end"]
    list_filter = ["status", "plan"]


@admin.register(TenantInvoice)
class TenantInvoiceAdmin(admin.ModelAdmin):
    list_display = ["hospital", "amount", "currency", "status", "issued_at", "paid_at"]
    list_filter = ["status"]
