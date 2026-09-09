import os
from celery import Celery
from kombu import Queue, Exchange
from packages.common.config import settings

# Celery Application Instance
celery_app = Celery(
    "codenter_sdr_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "apps.worker.tasks.test_tasks",
        "apps.worker.tasks.crawler_tasks",
        "apps.worker.tasks.crm_tasks",
        "apps.worker.tasks.send_email_tasks",
        "apps.worker.tasks.scheduler_tasks",
        "apps.worker.tasks.inbound_email",
        "apps.worker.tasks.crm_sync",
    ]
)

# Exchange definitions
default_exchange = Exchange("default", type="direct")
email_exchange = Exchange("email_send", type="direct")
crawler_exchange = Exchange("crawler", type="direct")
ai_exchange = Exchange("ai_tasks", type="direct")
sync_exchange = Exchange("sync", type="direct")

# Dedicated Queues
celery_app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("email_send", email_exchange, routing_key="email_send"),
    Queue("crawler", crawler_exchange, routing_key="crawler"),
    Queue("ai_tasks", ai_exchange, routing_key="ai_tasks"),
    Queue("sync", sync_exchange, routing_key="sync"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# Task routing
celery_app.conf.task_routes = {
    "apps.worker.tasks.send_email_tasks.*": {"queue": "email_send"},
    "apps.worker.tasks.inbound_email.*": {"queue": "ai_tasks"},
    "apps.worker.tasks.scheduler_tasks.*": {"queue": "default"},
    "apps.worker.tasks.crawler_tasks.*": {"queue": "crawler"},
    "apps.worker.tasks.crm_tasks.*": {"queue": "sync"},
    "apps.worker.tasks.crm_sync.*": {"queue": "sync"},
    "apps.worker.tasks.ai.*": {"queue": "ai_tasks"},
    "*": {"queue": "default"},
}

# Periodic Beat Scheduling
celery_app.conf.beat_schedule = {
    "evaluate-campaign-schedules-every-minute": {
        "task": "apps.worker.tasks.scheduler_tasks.evaluate_campaign_schedules_task",
        "schedule": 60.0,
    },
}

# Production configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,        # 5 minutes max
    task_soft_time_limit=240,   # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
