from datetime import timedelta

from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from apps.appointments.models import Appointment
from apps.clinical.models import PrescriptionItem
from apps.core.permissions import RoleRequiredMixin, TenantMemberRequiredMixin
from apps.core.roles import PHARMACY_ROLES
from apps.pharmacy.forms import DispenseForm, DrugForm, StockAdjustmentForm, StockInForm
from apps.pharmacy.models import EXPIRING_SOON_DAYS, Drug, StockBatch
from apps.pharmacy.services import (
    AlreadyDispensedError,
    DuplicateBatchError,
    InsufficientStockError,
    adjust_stock,
    dispense_item,
    drugs_with_stock,
    get_alert_counts,
    receive_stock,
)


class DrugListView(TenantMemberRequiredMixin, ListView):
    context_object_name = "drugs"
    paginate_by = 15

    def get_template_names(self):
        return ["pharmacy/_drug_table.html"] if self.request.htmx else ["pharmacy/drug_list.html"]

    def get_queryset(self):
        qs = drugs_with_stock(self.request.hospital).order_by("name")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(generic_name__icontains=q))
        alert_filter = self.request.GET.get("filter", "")
        if alert_filter == "low_stock":
            qs = qs.filter(Q(stock__lte=F("low_stock_threshold")) | Q(stock__isnull=True))
        elif alert_filter == "expiring":
            today = timezone.localdate()
            qs = qs.filter(
                batches__expiry_date__gte=today,
                batches__expiry_date__lte=today + timedelta(days=EXPIRING_SOON_DAYS),
                batches__quantity_remaining__gt=0,
            ).distinct()
        return qs

    def get_context_data(self, **kwargs):
        low_stock_count, expiring_count = get_alert_counts(self.request.hospital)
        return {
            **super().get_context_data(**kwargs),
            "current_q": self.request.GET.get("q", ""),
            "current_filter": self.request.GET.get("filter", ""),
            "low_stock_count": low_stock_count,
            "expiring_count": expiring_count,
            "can_manage": self.request.user.role in PHARMACY_ROLES,
        }


class DrugCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = PHARMACY_ROLES
    model = Drug
    form_class = DrugForm
    template_name = "pharmacy/drug_form.html"

    def form_valid(self, form):
        # Explicit pre-check rather than relying on ModelForm's automatic
        # constraint validation: hospital isn't a form field (it's set here,
        # not user-submitted), and by the time it's assigned the form has
        # already validated — a duplicate name+strength would otherwise hit
        # the DB's unique_drug_per_hospital constraint as a raw
        # IntegrityError instead of a friendly form error.
        name = form.cleaned_data["name"]
        strength = form.cleaned_data["strength"]
        if Drug.objects.filter(hospital=self.request.hospital, name=name, strength=strength).exists():
            form.add_error("name", "A drug with this name and strength already exists.")
            return self.form_invalid(form)
        form.instance.hospital = self.request.hospital
        return super().form_valid(form)


class DrugUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = PHARMACY_ROLES
    model = Drug
    form_class = DrugForm
    template_name = "pharmacy/drug_form.html"


class DrugDetailView(TenantMemberRequiredMixin, DetailView):
    model = Drug
    template_name = "pharmacy/drug_detail.html"
    context_object_name = "drug"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "batches": self.object.batches.all(),
            "movements": self.object.movements.select_related("batch", "performed_by")[:20],
            "can_manage": self.request.user.role in PHARMACY_ROLES,
        }


class StockInView(RoleRequiredMixin, FormView):
    allowed_roles = PHARMACY_ROLES
    form_class = StockInForm
    template_name = "pharmacy/stock_in.html"

    def dispatch(self, request, *args, **kwargs):
        self.drug = get_object_or_404(Drug, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "drug": self.drug}

    def form_valid(self, form):
        try:
            receive_stock(
                hospital=self.request.hospital,
                drug=self.drug,
                batch_number=form.cleaned_data["batch_number"],
                expiry_date=form.cleaned_data["expiry_date"],
                quantity=form.cleaned_data["quantity_received"],
                supplier=form.cleaned_data["supplier"],
                performed_by=self.request.user,
            )
        except DuplicateBatchError as exc:
            form.add_error("batch_number", str(exc))
            return self.form_invalid(form)
        return redirect("pharmacy:drug_detail", pk=self.drug.pk)


class StockAdjustmentView(RoleRequiredMixin, View):
    allowed_roles = PHARMACY_ROLES

    def post(self, request, pk):
        batch = get_object_or_404(StockBatch, pk=pk)
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                adjust_stock(
                    batch=batch,
                    quantity_delta=form.cleaned_data["quantity_delta"],
                    notes=form.cleaned_data["notes"],
                    performed_by=request.user,
                )
            except InsufficientStockError:
                pass
        return redirect("pharmacy:drug_detail", pk=batch.drug_id)


class BatchesForDrugView(TenantMemberRequiredMixin, View):
    """htmx endpoint backing the dispense form's batch picker."""

    def get(self, request):
        drug_id = request.GET.get("drug", "")
        batches = StockBatch.objects.filter(drug_id=drug_id, quantity_remaining__gt=0).order_by("expiry_date")
        return render(request, "pharmacy/_batch_field.html", {"batches": batches})


class DispenseQueueView(RoleRequiredMixin, ListView):
    allowed_roles = PHARMACY_ROLES
    context_object_name = "items"
    paginate_by = 15

    def get_template_names(self):
        return ["pharmacy/_dispense_table.html"] if self.request.htmx else ["pharmacy/dispense_queue.html"]

    def get_queryset(self):
        status = self.request.GET.get("status", "pending")
        qs = PrescriptionItem.objects.filter(
            consultation__appointment__status=Appointment.Status.COMPLETED
        ).select_related("consultation__appointment__patient", "consultation__appointment__doctor")
        if status == "pending":
            qs = qs.filter(dispense_record__isnull=True)
        elif status == "dispensed":
            qs = qs.filter(dispense_record__isnull=False)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(drug_name__icontains=q)
                | Q(consultation__appointment__patient__first_name__icontains=q)
                | Q(consultation__appointment__patient__last_name__icontains=q)
                | Q(consultation__appointment__patient__mrn__icontains=q)
            )
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_q": self.request.GET.get("q", ""),
            "current_status": self.request.GET.get("status", "pending"),
        }


class DispenseView(RoleRequiredMixin, FormView):
    allowed_roles = PHARMACY_ROLES
    form_class = DispenseForm
    template_name = "pharmacy/dispense_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(PrescriptionItem, pk=kwargs["item_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "hospital": self.request.hospital}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "item": self.item}

    def get(self, request, *args, **kwargs):
        if hasattr(self.item, "dispense_record"):
            return redirect("pharmacy:dispense_queue")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            dispense_item(
                prescription_item=self.item,
                drug=form.cleaned_data["drug"],
                batch=form.cleaned_data["batch"],
                quantity=form.cleaned_data["quantity"],
                performed_by=self.request.user,
            )
        except (AlreadyDispensedError, InsufficientStockError) as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return redirect("pharmacy:dispense_queue")
