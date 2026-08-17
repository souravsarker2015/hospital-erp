from django.urls import path

from apps.tenants import views

app_name = "tenants"

urlpatterns = [
    path("", views.PlanSelectView.as_view(), name="plan_select"),
    path("success/", views.SignupSuccessView.as_view(), name="signup_success"),
    path("<slug:plan_slug>/", views.HospitalRegisterView.as_view(), name="register"),
]
