import asyncio
from apps.worker.celery_app import celery_app
from apps.worker.middleware import retry_with_jitter
from apps.api.core.database import AsyncSessionLocal
from packages.website_intelligence.crawler_service import WebsiteCrawlerService

@celery_app.task(bind=True, name="apps.worker.tasks.crawler_tasks.run_website_scan_task")
@retry_with_jitter(max_retries=3, base_delay=2.0)
def run_website_scan_task(self, workspace_id: str, scan_id: str, base_url: str):
    """
    Celery background worker task for asynchronous website scanning.
    """
    async def _async_scan():
        try:
            async with AsyncSessionLocal() as session:
                return await WebsiteCrawlerService.run_scan(
                    workspace_id=workspace_id,
                    scan_id=scan_id,
                    base_url=base_url,
                    db=session
                )
        except Exception:
            pass

    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(_async_scan())
    except RuntimeError:
        return asyncio.run(_async_scan())
