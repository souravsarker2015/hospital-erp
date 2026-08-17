from django.conf import settings

from apps.core.nav import TENANT_NAV_ITEMS


def current_hospital(request):
    port = f":{request.get_port()}" if request.get_port() not in ("80", "443") else ""
    return {
        "current_hospital": getattr(request, "hospital", None),
        "marketing_home_url": f"{request.scheme}://{settings.PLATFORM_DOMAIN}{port}/",
        "tenant_nav_items": TENANT_NAV_ITEMS,
    }
