from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.permissions import RoleRequiredMixin, TenantMemberRequiredMixin
from apps.patients.forms import PatientForm
from apps.patients.models import Patient
from apps.patients.services import register_patient
from apps.users.models import User

FRONT_DESK_ROLES = [User.Role.ADMIN, User.Role.RECEPTIONIST, User.Role.NURSE]


class PatientListView(TenantMemberRequiredMixin, ListView):
    model = Patient
    context_object_name = "patients"
    paginate_by = 15

    def get_template_names(self):
        if self.request.htmx:
            return ["patients/_patient_table.html"]
        return ["patients/list.html"]

    def get_queryset(self):
        qs = Patient.objects.filter(is_active=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(phone_number__icontains=q)
                | Q(mrn__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_q": self.request.GET.get("q", ""),
            "can_register": self.request.user.role in FRONT_DESK_ROLES,
        }


class PatientCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = FRONT_DESK_ROLES
    model = Patient
    form_class = PatientForm
    template_name = "patients/form.html"

    def form_valid(self, form):
        self.object = register_patient(
            hospital=self.request.hospital,
            created_by=self.request.user,
            **form.cleaned_data,
        )
        return redirect(self.object)


class PatientUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = FRONT_DESK_ROLES
    model = Patient
    form_class = PatientForm
    template_name = "patients/form.html"


class PatientDetailView(TenantMemberRequiredMixin, DetailView):
    model = Patient
    template_name = "patients/detail.html"
    context_object_name = "patient"
