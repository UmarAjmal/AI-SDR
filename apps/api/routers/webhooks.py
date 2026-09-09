import base64
import json
import logging
from typing import Optional, Any
from fastapi import APIRouter, Request, Response, HTTPException, status, Query
from apps.worker.tasks.inbound_email import process_inbound_email_task

logger = logging.getLogger("codenter.api.webhooks")

router = APIRouter(prefix="/webhooks", tags=["Inbound Webhooks"])

@router.post("/inbound/{workspace_id}", status_code=status.HTTP_202_ACCEPTED)
async def handle_generic_inbound_webhook(workspace_id: str, request: Request):
    """
    Direct inbound webhook ingestion for email providers or test payloads.
    Dispatches Celery worker task for async background processing.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    process_inbound_email_task.delay(
        workspace_id=workspace_id,
        raw_payload=payload,
        provider="GENERIC"
    )

    return {"status": "accepted", "workspace_id": workspace_id}

@router.post("/google/{workspace_id}", status_code=status.HTTP_202_ACCEPTED)
async def handle_google_pubsub_webhook(workspace_id: str, request: Request):
    """
    Handles Google Cloud Pub/Sub push notifications for Gmail mailbox watch.
    Decodes message data and triggers background ingestion.
    """
    try:
        payload = await request.json()
        message = payload.get("message", {})
        data_b64 = message.get("data", "")
        if data_b64:
            decoded_json = json.loads(base64.b64decode(data_b64).decode("utf-8"))
        else:
            decoded_json = payload
    except Exception as e:
        logger.warning(f"Malformed Google Pub/Sub webhook: {e}")
        return {"status": "ignored"}

    process_inbound_email_task.delay(
        workspace_id=workspace_id,
        raw_payload=decoded_json,
        provider="GOOGLE"
    )

    return {"status": "accepted"}

@router.post("/microsoft/{workspace_id}")
async def handle_microsoft_graph_webhook(
    workspace_id: str,
    request: Request,
    validationToken: Optional[str] = Query(None)
):
    """
    Handles Microsoft Graph change notifications:
    - If validationToken is present, responds immediately with plain text token (Graph handshake).
    - Otherwise queues background ingestion for notification values.
    """
    if validationToken:
        return Response(content=validationToken, media_type="text/plain")

    try:
        payload = await request.json()
        value_list = payload.get("value", [])
        for item in value_list:
            process_inbound_email_task.delay(
                workspace_id=workspace_id,
                raw_payload=item,
                provider="MICROSOFT"
            )
    except Exception as e:
        logger.warning(f"Error handling Graph webhook: {e}")

    return Response(status_code=status.HTTP_202_ACCEPTED)
