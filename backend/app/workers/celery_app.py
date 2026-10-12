from typing import Any

from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
celery_app = Celery(
    "erp",
    broker=(settings.celery_broker_url or settings.redis_url).get_secret_value(),
    backend=(settings.celery_result_backend or settings.redis_url).get_secret_value(),
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_ignore_result=True,
    beat_schedule={},
)


def setup_worker_logging(**kwargs: Any) -> None:
    configure_logging(settings.log_level)


setup_logging.connect(setup_worker_logging)
