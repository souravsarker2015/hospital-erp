from django.urls import path

from apps.tenants import admin_views

app_name = "platform_admin"

urlpatterns = [
    path("", admin_views.TenantListView.as_view(), name="tenant_list"),
    path("<uuid:pk>/suspend/", admin_views.SuspendHospitalView.as_view(), name="tenant_suspend"),
    path("<uuid:pk>/activate/", admin_views.ActivateHospitalView.as_view(), name="tenant_activate"),
]
