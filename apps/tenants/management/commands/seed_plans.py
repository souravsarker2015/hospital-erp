from django.core.management.base import BaseCommand

from apps.tenants.models import Plan

PLANS = [
    dict(
        name="Starter", slug="starter",
        tagline="For small clinics getting off paper registers",
        price_monthly=29, max_users=5,
        includes_pharmacy=True, includes_lab=False, includes_wards=False,
        is_featured=False, sort_order=1,
    ),
    dict(
        name="Growth", slug="growth",
        tagline="For multi-doctor clinics running OPD at volume",
        price_monthly=79, max_users=25,
        includes_pharmacy=True, includes_lab=True, includes_wards=False,
        is_featured=True, sort_order=2,
    ),
    dict(
        name="Enterprise", slug="enterprise",
        tagline="For hospitals with wards, labs, and multiple departments",
        price_monthly=199, max_users=None,
        includes_pharmacy=True, includes_lab=True, includes_wards=True,
        is_featured=False, sort_order=3,
    ),
]


class Command(BaseCommand):
    help = "Seeds the Starter/Growth/Enterprise subscription plans shown on the marketing pricing page and signup flow. Safe to re-run."

    def handle(self, *args, **options):
        for plan_kwargs in PLANS:
            plan, created = Plan.objects.update_or_create(
                slug=plan_kwargs["slug"], defaults=plan_kwargs
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} plan: {plan.name} (${plan.price_monthly}/mo)"))
