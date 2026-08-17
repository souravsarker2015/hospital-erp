"""Public urlconf — active on the bare PLATFORM_DOMAIN (marketing site,
tenant signup, platform admin). Requests on a resolved hospital subdomain
are switched to config.urls_tenant by CurrentHospitalMiddleware."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("platform/", include("apps.tenants.urls_platform")),
    path("accounts/", include("apps.users.urls")),
    path("signup/", include("apps.tenants.urls")),
    path("", include("apps.marketing.urls")),
]
