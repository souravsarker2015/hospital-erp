from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView
from xhtml2pdf import pisa

from apps.clinical.models import LabOrder
from apps.core.permissions import RoleRequiredMixin, TenantMemberRequiredMixin
from apps.core.roles import ALL_STAFF_ROLES, LAB_ROLES
from apps.lab.forms import CollectSampleForm, LabTestForm, ResultEntryForm
from apps.lab.models import LabResult, LabTest
from apps.lab.services import AlreadyCollectedError, collect_sample, enter_result


class LabTestListView(TenantMemberRequiredMixin, ListView):
    context_object_name = "tests"
    paginate_by = 15

    def get_template_names(self):
        return ["lab/_test_table.html"] if self.request.htmx else ["lab/test_list.html"]

    def get_queryset(self):
        qs = LabTest.objects.filter(is_active=True).order_by("name")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_q": self.request.GET.get("q", ""),
            "can_manage": self.request.user.role in LAB_ROLES,
        }


class LabTestCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = LAB_ROLES
    model = LabTest
    form_class = LabTestForm
    template_name = "lab/test_form.html"

    def form_valid(self, form):
        # Same pre-check pattern as apps.pharmacy.views.DrugCreateView: the
        # hospital FK isn't a form field, so it's only set after is_valid()
        # runs — a duplicate test name would otherwise hit the DB's
        # unique_lab_test_per_hospital constraint as a raw IntegrityError.
        name = form.cleaned_data["name"]
        if LabTest.objects.filter(hospital=self.request.hospital, name=name).exists():
            form.add_error("name", "A test with this name already exists.")
            return self.form_invalid(form)
        form.instance.hospital = self.request.hospital
        return super().form_valid(form)


class LabTestUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = LAB_ROLES
    model = LabTest
    form_class = LabTestForm
    template_name = "lab/test_form.html"


class LabQueueView(TenantMemberRequiredMixin, ListView):
    context_object_name = "orders"
    paginate_by = 15

    def get_template_names(self):
        return ["lab/_queue_table.html"] if self.request.htmx else ["lab/queue.html"]

    def get_queryset(self):
        qs = (
            LabOrder.objects.exclude(status=LabOrder.Status.CANCELLED)
            .select_related("consultation__appointment__patient", "consultation__appointment__doctor", "lab_result__test")
            .order_by("-created_at")
        )
        status_filter = self.request.GET.get("status", "pending")
        if status_filter == "pending":
            qs = qs.filter(lab_result__isnull=True)
        elif status_filter == "collected":
            qs = qs.filter(lab_result__sample_status=LabResult.SampleStatus.COLLECTED)
        elif status_filter == "done":
            qs = qs.filter(lab_result__sample_status=LabResult.SampleStatus.RESULT_ENTERED)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(test_name__icontains=q)
                | Q(consultation__appointment__patient__first_name__icontains=q)
                | Q(consultation__appointment__patient__last_name__icontains=q)
                | Q(consultation__appointment__patient__mrn__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_q": self.request.GET.get("q", ""),
            "current_status": self.request.GET.get("status", "pending"),
            "can_manage": self.request.user.role in LAB_ROLES,
        }


class CollectSampleView(RoleRequiredMixin, FormView):
    allowed_roles = LAB_ROLES
    form_class = CollectSampleForm
    template_name = "lab/collect_sample.html"

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(LabOrder, pk=kwargs["order_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if hasattr(self.order, "lab_result"):
            return redirect("lab:queue")
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "hospital": self.request.hospital}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "order": self.order}

    def form_valid(self, form):
        try:
            collect_sample(lab_order=self.order, test=form.cleaned_data["test"], performed_by=self.request.user)
        except AlreadyCollectedError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect("lab:queue")


class EnterResultView(RoleRequiredMixin, FormView):
    allowed_roles = LAB_ROLES
    form_class = ResultEntryForm
    template_name = "lab/enter_result.html"

    def dispatch(self, request, *args, **kwargs):
        self.order = get_object_or_404(LabOrder, pk=kwargs["order_pk"])
        if not hasattr(self.order, "lab_result"):
            return redirect("lab:collect_sample", order_pk=self.order.pk)
        self.result = self.order.lab_result
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.result}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "order": self.order, "result": self.result}

    def form_valid(self, form):
        enter_result(
            lab_result=self.result,
            result_value=form.cleaned_data["result_value"],
            result_notes=form.cleaned_data["result_notes"],
            is_abnormal=form.cleaned_data["is_abnormal"],
            performed_by=self.request.user,
        )
        return redirect("lab:queue")


class LabReportPDFView(RoleRequiredMixin, View):
    allowed_roles = ALL_STAFF_ROLES

    def get(self, request, *args, **kwargs):
        order = get_object_or_404(LabOrder, pk=kwargs["order_pk"])
        if not hasattr(order, "lab_result") or order.lab_result.sample_status != LabResult.SampleStatus.RESULT_ENTERED:
            return redirect("lab:queue")

        html = render_to_string("lab/report_pdf.html", {"order": order, "result": order.lab_result})
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="lab-report-{order.pk}.pdf"'
        pisa.CreatePDF(html, dest=response)
        return response
