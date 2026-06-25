import logging
import sys

from app.config import settings


def setup_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Quieten noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("portflow")


def log_prediction_event(
    model_name: str,
    model_version: str,
    vessel_id: int,
    predicted_value: float | None,
    confidence: float | None,
    request_id: str | None = None,
) -> None:
    logger.info(
        "PREDICTION | model=%s v%s | vessel_id=%d | value=%s | confidence=%s | request_id=%s",
        model_name,
        model_version,
        vessel_id,
        predicted_value,
        confidence,
        request_id or "n/a",
    )


def log_error(request_id: str, error: Exception, context: str = "") -> None:
    logger.error(
        "ERROR | request_id=%s | context=%s | error=%s: %s",
        request_id,
        context,
        type(error).__name__,
        str(error),
    )
