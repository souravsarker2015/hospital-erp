from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.appointments.models import Appointment
from apps.billing.forms import AddLineItemForm, RecordPaymentForm, ServiceItemForm
from apps.billing.models import Invoice, InvoiceLineItem, ServiceItem
from apps.billing.services import (
    AppointmentNotCompletedError,
    InvoiceAlreadyExistsError,
    OverpaymentError,
    add_line_item,
    generate_invoice,
    record_payment,
)
from apps.core.permissions import RoleRequiredMixin, TenantMemberRequiredMixin
from apps.core.roles import BILLING_ROLES


class InvoiceListView(TenantMemberRequiredMixin, ListView):
    context_object_name = "invoices"
    paginate_by = 15

    def get_template_names(self):
        return ["billing/_invoice_table.html"] if self.request.htmx else ["billing/invoice_list.html"]

    def get_queryset(self):
        qs = Invoice.objects.select_related("patient").order_by("-created_at")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q)
                | Q(patient__first_name__icontains=q)
                | Q(patient__last_name__icontains=q)
                | Q(patient__mrn__icontains=q)
            )
        status = self.request.GET.get("status", "")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "current_q": self.request.GET.get("q", ""),
            "current_status": self.request.GET.get("status", ""),
            "status_choices": Invoice.Status.choices,
            "can_manage": self.request.user.role in BILLING_ROLES,
        }


class BillingQueueView(RoleRequiredMixin, ListView):
    allowed_roles = BILLING_ROLES
    context_object_name = "appointments"
    paginate_by = 15

    def get_template_names(self):
        return ["billing/_queue_table.html"] if self.request.htmx else ["billing/queue.html"]

    def get_queryset(self):
        qs = (
            Appointment.objects.filter(status=Appointment.Status.COMPLETED, invoice__isnull=True)
            .select_related("patient", "doctor")
            .order_by("-appointment_date", "-token_number")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(patient__first_name__icontains=q) | Q(patient__last_name__icontains=q) | Q(patient__mrn__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "current_q": self.request.GET.get("q", "")}


class GenerateInvoiceView(RoleRequiredMixin, View):
    allowed_roles = BILLING_ROLES

    def post(self, request, appointment_pk):
        appointment = get_object_or_404(Appointment, pk=appointment_pk)
        try:
            invoice = generate_invoice(hospital=request.hospital, appointment=appointment, created_by=request.user)
        except (AppointmentNotCompletedError, InvoiceAlreadyExistsError):
            return redirect("billing:queue")
        return redirect("billing:detail", pk=invoice.pk)


class InvoiceDetailView(TenantMemberRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "line_item_form": AddLineItemForm(hospital=self.request.hospital),
            "payment_form": RecordPaymentForm(),
            "can_manage": self.request.user.role in BILLING_ROLES,
        }


class AddLineItemView(RoleRequiredMixin, View):
    allowed_roles = BILLING_ROLES

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = AddLineItemForm(request.POST, hospital=request.hospital)
        if form.is_valid():
            service_item = form.cleaned_data["service_item"]
            item_type = (
                InvoiceLineItem.ItemType.CONSULTATION
                if service_item.category == ServiceItem.Category.CONSULTATION
                else InvoiceLineItem.ItemType.OTHER
            )
            add_line_item(
                invoice=invoice,
                item_type=item_type,
                description=service_item.name,
                quantity=form.cleaned_data["quantity"],
                unit_price=service_item.price,
                service_item=service_item,
            )
        return redirect("billing:detail", pk=invoice.pk)


class RecordPaymentView(RoleRequiredMixin, View):
    allowed_roles = BILLING_ROLES

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        form = RecordPaymentForm(request.POST)
        if form.is_valid():
            try:
                record_payment(
                    invoice=invoice,
                    method=form.cleaned_data["method"],
                    amount=form.cleaned_data["amount"],
                    reference=form.cleaned_data["reference"],
                    received_by=request.user,
                )
            except OverpaymentError as exc:
                context = {
                    "invoice": invoice,
                    "line_item_form": AddLineItemForm(hospital=request.hospital),
                    "payment_form": form,
                    "can_manage": True,
                    "payment_error": str(exc),
                }
                return render(request, "billing/invoice_detail.html", context)
        return redirect("billing:detail", pk=invoice.pk)


class InvoicePrintView(TenantMemberRequiredMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_print.html"
    context_object_name = "invoice"


class ServiceItemListView(TenantMemberRequiredMixin, ListView):
    context_object_name = "services"
    paginate_by = 20

    def get_queryset(self):
        return ServiceItem.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "can_manage": self.request.user.role in BILLING_ROLES}

    template_name = "billing/service_list.html"


class ServiceItemCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = BILLING_ROLES
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = "billing/service_form.html"

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        if ServiceItem.objects.filter(hospital=self.request.hospital, name=name).exists():
            form.add_error("name", "A service item with this name already exists.")
            return self.form_invalid(form)
        form.instance.hospital = self.request.hospital
        return super().form_valid(form)


class ServiceItemUpdateView(RoleRequiredMixin, UpdateView):
    allowed_roles = BILLING_ROLES
    model = ServiceItem
    form_class = ServiceItemForm
    template_name = "billing/service_form.html"
