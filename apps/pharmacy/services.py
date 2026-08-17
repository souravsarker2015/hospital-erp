import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.core.logging_utils import log_context
from apps.pharmacy.models import EXPIRING_SOON_DAYS, DispenseRecord, Drug, StockBatch, StockMovement

logger = logging.getLogger("pharmacy")


class PharmacyError(Exception):
    pass


class AlreadyDispensedError(PharmacyError):
    pass


class InsufficientStockError(PharmacyError):
    pass


class DuplicateBatchError(PharmacyError):
    pass


@transaction.atomic
def receive_stock(*, hospital, drug, batch_number, expiry_date, quantity, supplier="", performed_by=None) -> StockBatch:
    if StockBatch.objects.filter(hospital=hospital, drug=drug, batch_number=batch_number).exists():
        raise DuplicateBatchError(f"Batch '{batch_number}' already exists for {drug.name}.")

    batch = StockBatch.objects.create(
        hospital=hospital,
        drug=drug,
        batch_number=batch_number,
        expiry_date=expiry_date,
        quantity_received=quantity,
        quantity_remaining=quantity,
        supplier=supplier,
    )
    StockMovement.objects.create(
        hospital=hospital,
        drug=drug,
        batch=batch,
        movement_type=StockMovement.MovementType.STOCK_IN,
        quantity=quantity,
        performed_by=performed_by,
    )
    logger.info(
        "pharmacy.stock_in",
        extra=log_context(hospital_id=hospital.id, user_id=getattr(performed_by, "id", None), drug=drug.name, quantity=quantity),
    )
    return batch


@transaction.atomic
def dispense_item(*, prescription_item, drug, batch, quantity: int, performed_by=None) -> DispenseRecord:
    if hasattr(prescription_item, "dispense_record"):
        raise AlreadyDispensedError("This prescription item has already been dispensed.")

    locked_batch = StockBatch.objects.select_for_update().get(pk=batch.pk)
    if quantity > locked_batch.quantity_remaining:
        raise InsufficientStockError(
            f"Only {locked_batch.quantity_remaining} left in batch {locked_batch.batch_number}."
        )

    locked_batch.quantity_remaining -= quantity
    locked_batch.save(update_fields=["quantity_remaining", "updated_at"])

    record = DispenseRecord.objects.create(
        hospital=prescription_item.hospital,
        prescription_item=prescription_item,
        drug=drug,
        batch=locked_batch,
        quantity=quantity,
        dispensed_by=performed_by,
    )
    StockMovement.objects.create(
        hospital=prescription_item.hospital,
        drug=drug,
        batch=locked_batch,
        movement_type=StockMovement.MovementType.DISPENSE,
        quantity=-quantity,
        notes=f"Rx: {prescription_item.drug_name}",
        performed_by=performed_by,
    )
    logger.info(
        "pharmacy.dispensed",
        extra=log_context(hospital_id=prescription_item.hospital_id, user_id=getattr(performed_by, "id", None), drug=drug.name, quantity=quantity),
    )
    return record


@transaction.atomic
def adjust_stock(*, batch, quantity_delta: int, notes: str, performed_by=None) -> StockBatch:
    locked_batch = StockBatch.objects.select_for_update().get(pk=batch.pk)
    new_remaining = locked_batch.quantity_remaining + quantity_delta
    if new_remaining < 0:
        raise InsufficientStockError("Adjustment would take this batch below zero.")

    locked_batch.quantity_remaining = new_remaining
    locked_batch.save(update_fields=["quantity_remaining", "updated_at"])
    StockMovement.objects.create(
        hospital=locked_batch.hospital,
        drug=locked_batch.drug,
        batch=locked_batch,
        movement_type=StockMovement.MovementType.ADJUSTMENT,
        quantity=quantity_delta,
        notes=notes,
        performed_by=performed_by,
    )
    return locked_batch


def drugs_with_stock(hospital):
    """Drug queryset annotated with `stock` = total remaining across
    non-expired batches, for list/filter views."""
    today = timezone.localdate()
    return Drug.objects.filter(hospital=hospital, is_active=True).annotate(
        stock=Sum("batches__quantity_remaining", filter=Q(batches__expiry_date__gte=today))
    )


def get_alert_counts(hospital) -> tuple[int, int]:
    today = timezone.localdate()
    low_stock_count = drugs_with_stock(hospital).filter(
        Q(stock__lte=F("low_stock_threshold")) | Q(stock__isnull=True)
    ).count()
    expiring_count = (
        StockBatch.objects.filter(
            hospital=hospital,
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=EXPIRING_SOON_DAYS),
            quantity_remaining__gt=0,
        )
        .values("drug")
        .distinct()
        .count()
    )
    return low_stock_count, expiring_count
