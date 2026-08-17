import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.logging_utils import log_context
from apps.tenants.models import Hospital, Subscription

logger = logging.getLogger("tenants")

TRIAL_DAYS = 14


class SubdomainTakenError(Exception):
    pass


@transaction.atomic
def provision_hospital(
    *,
    hospital_name: str,
    subdomain: str,
    contact_email: str,
    plan,
    admin_username: str,
    admin_password: str,
    admin_first_name: str = "",
    admin_last_name: str = "",
):
    """Creates a Hospital + trial Subscription + its first Admin user.

    Shared-schema tenancy means "provisioning" is just inserting rows —
    there is no Postgres schema to create or migrate, unlike django-tenants.
    """
    from apps.users.models import User

    if Hospital.objects.filter(subdomain=subdomain).exists():
        raise SubdomainTakenError(f"Subdomain '{subdomain}' is already taken.")

    hospital = Hospital.objects.create(
        name=hospital_name,
        subdomain=subdomain,
        contact_email=contact_email,
        plan=plan,
        subscription_status=Hospital.SubscriptionStatus.TRIAL,
    )
    Subscription.objects.create(
        hospital=hospital,
        plan=plan,
        status=Subscription.Status.TRIALING,
        trial_ends_at=timezone.now() + timedelta(days=TRIAL_DAYS),
    )
    admin_user = User.objects.create_user(
        username=admin_username,
        email=contact_email,
        password=admin_password,
        first_name=admin_first_name,
        last_name=admin_last_name,
        hospital=hospital,
        role=User.Role.ADMIN,
    )

    logger.info(
        "hospital.provisioned",
        extra=log_context(hospital_id=hospital.id, user_id=admin_user.id, plan=plan.slug),
    )
    return hospital, admin_user


def suspend_hospital(hospital: Hospital) -> Hospital:
    hospital.is_active = False
    hospital.subscription_status = Hospital.SubscriptionStatus.SUSPENDED
    hospital.save(update_fields=["is_active", "subscription_status", "updated_at"])
    logger.info("hospital.suspended", extra=log_context(hospital_id=hospital.id))
    return hospital


def activate_hospital(hospital: Hospital) -> Hospital:
    hospital.is_active = True
    hospital.subscription_status = Hospital.SubscriptionStatus.ACTIVE
    hospital.save(update_fields=["is_active", "subscription_status", "updated_at"])
    logger.info("hospital.activated", extra=log_context(hospital_id=hospital.id))
    return hospital
