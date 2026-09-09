from apps.worker.celery_app import celery_app
from apps.worker.middleware import retry_with_jitter

@celery_app.task(bind=True, name="apps.worker.tasks.test_tasks.ping_workspace_task")
@retry_with_jitter(max_retries=3, base_delay=1.0)
def ping_workspace_task(self, workspace_id: str, message: str = "ping"):
    """
    Test background task demonstrating tenant context deserialization,
    logging, and successful return payload.
    """
    return {
        "status": "SUCCESS",
        "workspace_id": workspace_id,
        "message": f"Pong: {message}",
        "task_id": self.request.id,
    }
