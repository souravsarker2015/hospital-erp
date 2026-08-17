"""Structured-logging helpers.

Convention: every state-changing service call logs at INFO with hospital_id
and user_id in the record, e.g.

    logger.info(
        "patient.registered",
        extra=log_context(hospital_id=hospital.id, user_id=user.id),
    )
"""

import logging


def log_context(*, hospital_id=None, user_id=None, **extra):
    return {"hospital_id": str(hospital_id), "user_id": str(user_id), **extra}


class ContextDefaultsFilter(logging.Filter):
    """Guarantees hospital_id/user_id attributes exist on every record so the
    formatter never raises when a log call omits them."""

    def filter(self, record: logging.LogRecord) -> bool:
        for attr in ("hospital_id", "user_id"):
            if not hasattr(record, attr):
                setattr(record, attr, "-")
        return True
