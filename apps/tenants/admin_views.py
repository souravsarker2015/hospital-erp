"""Platform-owner console: /platform/ — list every tenant, filter/search,
suspend or activate. Gated by PlatformStaffRequiredMixin, reachable only on
the bare PLATFORM_DOMAIN (config.urls, not config.urls_tenant)."""

from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from apps.core.permissions import PlatformStaffRequiredMixin
from apps.tenants.models import Hospital, Plan
from apps.tenants.services import activate_hospital, suspend_hospital


class TenantListView(PlatformStaffRequiredMixin, ListView):
    model = Hospital
    context_object_name = "hospitals"
    paginate_by = 15

    def get_template_names(self):
        if self.request.htmx:
            return ["tenants/platform_admin/_tenant_table.html"]
        return ["tenants/platform_admin/tenant_list.html"]

    def get_queryset(self):
        qs = Hospital.objects.select_related("plan").order_by("name")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        plan_slug = self.request.GET.get("plan", "")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(subdomain__icontains=q) | Q(contact_email__icontains=q)
            )
        if status:
            qs = qs.filter(subscription_status=status)
        if plan_slug:
            qs = qs.filter(plan__slug=plan_slug)
        return qs

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "plans": Plan.objects.all(),
            "status_choices": Hospital.SubscriptionStatus.choices,
            "current_q": self.request.GET.get("q", ""),
            "current_status": self.request.GET.get("status", ""),
            "current_plan": self.request.GET.get("plan", ""),
        }


class SuspendHospitalView(PlatformStaffRequiredMixin, View):
    def post(self, request, pk):
        hospital = suspend_hospital(get_object_or_404(Hospital, pk=pk))
        return render(request, "tenants/platform_admin/_tenant_row.html", {"hospital": hospital})


class ActivateHospitalView(PlatformStaffRequiredMixin, View):
    def post(self, request, pk):
        hospital = activate_hospital(get_object_or_404(Hospital, pk=pk))
        return render(request, "tenants/platform_admin/_tenant_row.html", {"hospital": hospital})
