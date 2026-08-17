import logging

from django.db import transaction

from apps.appointments.models import Appointment
from apps.billing.models import Invoice, InvoiceLineItem, Payment, ServiceItem
from apps.core.logging_utils import log_context
from apps.tenants.models import Hospital

logger = logging.getLogger("billing")


class BillingError(Exception):
    pass


class InvoiceAlreadyExistsError(BillingError):
    pass


class AppointmentNotCompletedError(BillingError):
    pass


class OverpaymentError(BillingError):
    pass


def _next_invoice_number(hospital: Hospital) -> str:
    locked_hospital = Hospital.objects.select_for_update().get(pk=hospital.pk)
    locked_hospital.last_invoice_number += 1
    locked_hospital.save(update_fields=["last_invoice_number"])
    prefix = (locked_hospital.subdomain[:3] or "INV").upper()
    return f"{prefix}-INV-{locked_hospital.last_invoice_number:06d}"


@transaction.atomic
def generate_invoice(*, hospital: Hospital, appointment: Appointment, created_by=None) -> Invoice:
    if appointment.status != Appointment.Status.COMPLETED:
        raise AppointmentNotCompletedError("The appointment must be completed before it can be invoiced.")
    if hasattr(appointment, "invoice"):
        raise InvoiceAlreadyExistsError("This appointment has already been invoiced.")

    invoice = Invoice.objects.create(
        hospital=hospital,
        invoice_number=_next_invoice_number(hospital),
        patient=appointment.patient,
        appointment=appointment,
        created_by=created_by,
    )

    consultation = getattr(appointment, "consultation", None)
    if consultation is not None:
        for item in consultation.prescription_items.all():
            record = getattr(item, "dispense_record", None)
            if record is None:
                continue
            InvoiceLineItem.objects.create(
                hospital=hospital,
                invoice=invoice,
                item_type=InvoiceLineItem.ItemType.PHARMACY,
                description=record.drug.name,
                quantity=record.quantity,
                unit_price=record.drug.unit_price,
                dispense_record=record,
            )

        for order in consultation.lab_orders.exclude(status="cancelled"):
            result = getattr(order, "lab_result", None)
            if result is None:
                continue
            InvoiceLineItem.objects.create(
                hospital=hospital,
                invoice=invoice,
                item_type=InvoiceLineItem.ItemType.LAB,
                description=result.test.name,
                quantity=1,
                unit_price=result.test.price,
                lab_order=order,
            )

    consultation_fees = ServiceItem.objects.filter(
        hospital=hospital, category=ServiceItem.Category.CONSULTATION, is_active=True
    )
    if consultation_fees.count() == 1:
        fee = consultation_fees.first()
        InvoiceLineItem.objects.create(
            hospital=hospital,
            invoice=invoice,
            item_type=InvoiceLineItem.ItemType.CONSULTATION,
            description=fee.name,
            quantity=1,
            unit_price=fee.price,
            service_item=fee,
        )

    logger.info(
        "billing.invoice_generated",
        extra=log_context(hospital_id=hospital.id, user_id=getattr(created_by, "id", None), invoice=invoice.invoice_number),
    )
    return invoice


def add_line_item(*, invoice: Invoice, item_type: str, description: str, quantity: int, unit_price, service_item=None) -> InvoiceLineItem:
    line_item = InvoiceLineItem.objects.create(
        hospital=invoice.hospital,
        invoice=invoice,
        item_type=item_type,
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        service_item=service_item,
    )
    # A new charge can un-pay an already-paid invoice, so recompute status
    # the same way record_payment does.
    recompute_invoice_status(invoice)
    return line_item


def recompute_invoice_status(invoice: Invoice) -> Invoice:
    due = invoice.amount_due
    if due <= 0 and invoice.total_amount > 0:
        invoice.status = Invoice.Status.PAID
    elif invoice.amount_paid > 0:
        invoice.status = Invoice.Status.PARTIALLY_PAID
    else:
        invoice.status = Invoice.Status.UNPAID
    invoice.save(update_fields=["status", "updated_at"])
    return invoice


@transaction.atomic
def record_payment(*, invoice: Invoice, method: str, amount, reference: str = "", received_by=None) -> Payment:
    locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if amount <= 0:
        raise OverpaymentError("Payment amount must be positive.")
    if amount > locked_invoice.amount_due:
        raise OverpaymentError(f"Amount exceeds the {locked_invoice.amount_due} still due.")

    payment = Payment.objects.create(
        hospital=locked_invoice.hospital,
        invoice=locked_invoice,
        method=method,
        amount=amount,
        reference=reference,
        received_by=received_by,
    )
    recompute_invoice_status(locked_invoice)
    logger.info(
        "billing.payment_recorded",
        extra=log_context(hospital_id=locked_invoice.hospital_id, user_id=getattr(received_by, "id", None), amount=str(amount)),
    )
    return payment
