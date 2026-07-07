from celery import Celery

from app.core.config import settings
from app.workers.beat_schedule import BEAT_SCHEDULE

celery_app = Celery(
    "social",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.email_tasks", "app.tasks.cleanup_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule=BEAT_SCHEDULE,
)
