from django.views.generic import TemplateView

from apps.core.permissions import TenantMemberRequiredMixin
from apps.dashboard.widgets import widgets_for_role


class DashboardHomeView(TenantMemberRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "hospital": self.request.hospital,
            "widgets": widgets_for_role(self.request.user.role),
        }
