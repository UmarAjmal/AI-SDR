import asyncio
from apps.worker.celery_app import celery_app
from apps.worker.middleware import retry_with_jitter
from apps.api.core.database import AsyncSessionLocal
from packages.crm.sync_service import CRMSyncService
from apps.worker.tasks.crm_sync import sync_lead_outcome_to_crm_task

@celery_app.task(bind=True, name="apps.worker.tasks.crm_tasks.sync_crm_leads_task")
@retry_with_jitter(max_retries=3, base_delay=2.0)
def sync_crm_leads_task(self, workspace_id: str, connection_id: str):
    """
    Celery background worker task for asynchronous CRM lead synchronization.
    """
    async def _async_sync():
        try:
            async with AsyncSessionLocal() as session:
                return await CRMSyncService.sync_connection(
                    workspace_id=workspace_id,
                    connection_id=connection_id,
                    db=session
                )
        except Exception:
            pass

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(_async_sync())
    except RuntimeError:
        return asyncio.run(_async_sync())
