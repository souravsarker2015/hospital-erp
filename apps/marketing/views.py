from django.views.generic import TemplateView

from apps.tenants.models import Plan

FAQS = [
    (
        "Is my hospital's data isolated from other hospitals on the platform?",
        "Yes. Every hospital gets its own subdomain and every record in the system is scoped to "
        "that hospital — staff and patients from one hospital can never see another hospital's data.",
    ),
    (
        "Can I import our existing patient records?",
        "Yes, we support CSV import for patient demographics during onboarding, and our team can "
        "help with a one-time migration for larger datasets.",
    ),
    (
        "Do you support insurance billing?",
        "Insurance payment tracking is available on the invoice — mark a bill as insurance-covered "
        "and record the claim reference. Full claims integration is on our roadmap.",
    ),
    (
        "What happens after my 14-day trial ends?",
        "You'll be prompted to choose a paid plan to keep your workspace active. Nothing is "
        "deleted — your data stays intact while you decide.",
    ),
    (
        "Can multiple doctors and receptionists use it at the same time?",
        "Yes — every staff member gets their own login and role, and the OPD queue, pharmacy "
        "stock and billing all update live for everyone at once.",
    ),
]


class HomeView(TemplateView):
    template_name = "marketing/home.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "plans": Plan.objects.filter(is_active=True),
            "faqs": FAQS,
        }
