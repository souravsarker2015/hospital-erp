from django.utils import timezone
from django.views.generic import TemplateView

from apps.core.permissions import TenantMemberRequiredMixin
from apps.dashboard.services import (
    appointment_status_chart,
    bed_occupancy_chart,
    revenue_last_7_days_chart,
    widgets_for_user,
)
from apps.users.models import User


class DashboardHomeView(TenantMemberRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        hospital = self.request.hospital
        user = self.request.user
        context = {
            **super().get_context_data(**kwargs),
            "hospital": hospital,
            "widgets": widgets_for_user(hospital, user),
        }

        if user.role == User.Role.ADMIN:
            context["revenue_chart"] = revenue_last_7_days_chart()
            context["occupancy_chart"] = bed_occupancy_chart()
        elif user.role == User.Role.ACCOUNTANT:
            context["revenue_chart"] = revenue_last_7_days_chart()
        elif user.role == User.Role.DOCTOR:
            context["status_chart"] = appointment_status_chart(timezone.localdate(), doctor=user)

        return context
