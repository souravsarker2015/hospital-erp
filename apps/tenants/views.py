from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from apps.tenants.forms import HospitalSignupForm
from apps.tenants.models import Hospital, Plan
from apps.tenants.services import SubdomainTakenError, provision_hospital


class PlanSelectView(TemplateView):
    template_name = "tenants/plan_select.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "plans": Plan.objects.filter(is_active=True)}


class HospitalRegisterView(SingleObjectMixin, FormView):
    template_name = "tenants/register.html"
    form_class = HospitalSignupForm
    model = Plan
    slug_field = "slug"
    slug_url_kwarg = "plan_slug"
    context_object_name = "plan"

    def get_queryset(self):
        return Plan.objects.filter(is_active=True)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(plan=self.object, **kwargs)

    def form_valid(self, form):
        plan = self.object
        try:
            hospital, admin_user = provision_hospital(
                hospital_name=form.cleaned_data["hospital_name"],
                subdomain=form.cleaned_data["subdomain"],
                contact_email=form.cleaned_data["contact_email"],
                plan=plan,
                admin_username=form.cleaned_data["admin_username"],
                admin_password=form.cleaned_data["admin_password1"],
                admin_first_name=form.cleaned_data["admin_first_name"],
                admin_last_name=form.cleaned_data["admin_last_name"],
            )
        except SubdomainTakenError:
            form.add_error("subdomain", "That subdomain was just taken. Please choose another.")
            return self.form_invalid(form)

        port = f":{self.request.get_port()}" if self.request.get_port() not in ("80", "443") else ""
        self.request.session["signup_success"] = {
            "hospital_name": hospital.name,
            "admin_username": admin_user.username,
            "login_url": f"{self.request.scheme}://{hospital.subdomain}.{settings.PLATFORM_DOMAIN}{port}{reverse('users:login')}",
        }
        return redirect("tenants:signup_success")


class SignupSuccessView(TemplateView):
    template_name = "tenants/signup_success.html"

    def get(self, request, *args, **kwargs):
        data = request.session.pop("signup_success", None)
        if not data:
            raise Http404
        return render(request, self.template_name, data)
