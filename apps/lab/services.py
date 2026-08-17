import logging

from django.db import transaction
from django.utils import timezone

from apps.core.logging_utils import log_context
from apps.lab.models import LabResult

logger = logging.getLogger("lab")


class LabError(Exception):
    pass


class AlreadyCollectedError(LabError):
    pass


@transaction.atomic
def collect_sample(*, lab_order, test, performed_by=None) -> LabResult:
    if hasattr(lab_order, "lab_result"):
        raise AlreadyCollectedError("A sample has already been recorded for this order.")

    result = LabResult.objects.create(
        hospital=lab_order.hospital,
        lab_order=lab_order,
        test=test,
        sample_status=LabResult.SampleStatus.COLLECTED,
        sample_collected_at=timezone.now(),
        sample_collected_by=performed_by,
    )
    logger.info(
        "lab.sample_collected",
        extra=log_context(hospital_id=lab_order.hospital_id, user_id=getattr(performed_by, "id", None), test=test.name),
    )
    return result


def enter_result(*, lab_result: LabResult, result_value: str, result_notes: str = "", is_abnormal: bool = False, performed_by=None) -> LabResult:
    lab_result.result_value = result_value
    lab_result.result_notes = result_notes
    lab_result.is_abnormal = is_abnormal
    lab_result.sample_status = LabResult.SampleStatus.RESULT_ENTERED
    lab_result.result_entered_at = timezone.now()
    lab_result.result_entered_by = performed_by
    lab_result.save()
    logger.info(
        "lab.result_entered",
        extra=log_context(hospital_id=lab_result.hospital_id, user_id=getattr(performed_by, "id", None), test=lab_result.test.name),
    )
    return lab_result
