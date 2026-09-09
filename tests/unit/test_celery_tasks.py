import pytest
from apps.worker.celery_app import celery_app
from apps.worker.tasks.test_tasks import ping_workspace_task

def test_celery_task_execution_with_tenant_context():
    # Configure Celery in eager mode for unit testing
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    workspace_id = "test-ws-uuid-777"
    result = ping_workspace_task.delay(workspace_id=workspace_id, message="milestone-1-verify")

    assert result.successful()
    output = result.get()
    assert output["status"] == "SUCCESS"
    assert output["workspace_id"] == workspace_id
    assert "Pong: milestone-1-verify" in output["message"]
    assert output["task_id"] is not None
