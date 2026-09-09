from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.core.database import get_db
from apps.api.core.dependencies import get_current_workspace_context, require_role, WorkspaceContext
from packages.common.models.workspace import WorkspaceRole
from packages.common.models.crm import CRMLead
from packages.common.models.email import EmailThread, EmailMessage
from packages.common.models.knowledge import KnowledgeChunk, BusinessProfile
from packages.ai.schemas import (
    DraftGenerationRequest,
    DraftGenerationResponse,
    IntentClassificationResult,
    InboundReplyDraft,
    ClaimVerificationResult,
    OutboundEmailDraft
)
from packages.ai.generation_service import AIPersonalizationService
from packages.ai.intent_classifier import IntentClassifier
from packages.ai.reply_agent import GroundedReplyAgent
from packages.ai.verifier import ClaimVerifier

router = APIRouter(prefix="/ai", tags=["AI Personalization & Intelligence"])

class VerifyClaimsRequest(BaseModel):
    claims: list[str]
    draft_text: str = ""

class ClassifyIntentRequest(BaseModel):
    subject: str = ""
    reply_text: str

class GenerateReplyRequest(BaseModel):
    thread_id: str
    inbound_message_id: str

@router.post("/generate-draft", response_model=DraftGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_outbound_draft(
    payload: DraftGenerationRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a personalized, bounded-context outbound email draft with strict
    claim verification and hallucination filter.
    """
    try:
        draft, telemetry, chunk_ids = await AIPersonalizationService.generate_outbound_draft(
            workspace_id=ctx.workspace_id,
            lead_id=payload.lead_id,
            campaign_step_id=payload.campaign_step_id,
            custom_instructions=payload.custom_instructions,
            db=db
        )
        return DraftGenerationResponse(
            draft=draft,
            telemetry=telemetry,
            knowledge_chunk_ids=chunk_ids,
            citations=chunk_ids
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Draft generation failed: {str(e)}")

@router.post("/verify-claims", response_model=ClaimVerificationResult)
async def verify_claims_endpoint(
    payload: VerifyClaimsRequest,
    ctx: WorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies factual claims against the workspace knowledge chunks and claims policy.
    """
    chunks_res = await db.execute(
        select(KnowledgeChunk.content).where(KnowledgeChunk.workspace_id == ctx.workspace_id)
    )
    chunk_texts = chunks_res.scalars().all()

    bp_res = await db.execute(
        select(BusinessProfile).where(
            BusinessProfile.workspace_id == ctx.workspace_id,
            BusinessProfile.is_active == True
        )
    )
    bp = bp_res.scalars().first()

    mock_draft = OutboundEmailDraft(
        subject="Verification Test",
        body=payload.draft_text,
        claims_used=payload.claims,
        cta="Test",
        confidence=1.0
    )

    return ClaimVerifier.verify_draft(
        draft=mock_draft,
        retrieved_chunk_texts=chunk_texts,
        business_profile=bp
    )

@router.post("/classify-intent", response_model=IntentClassificationResult)
async def classify_intent_endpoint(
    payload: ClassifyIntentRequest,
    ctx: WorkspaceContext = Depends(get_current_workspace_context)
):
    """
    Classifies prospect reply across the 14-intent taxonomy with pre-LLM opt-out check.
    """
    return await IntentClassifier.classify_reply(
        text=payload.reply_text,
        subject=payload.subject,
        workspace_id=ctx.workspace_id
    )

@router.post("/generate-reply", response_model=InboundReplyDraft)
async def generate_reply_endpoint(
    payload: GenerateReplyRequest,
    ctx: WorkspaceContext = Depends(require_role([WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a grounded contextual reply with citations for an inbound prospect message.
    """
    # Fetch thread and message
    th_res = await db.execute(
        select(EmailThread).where(
            EmailThread.id == payload.thread_id,
            EmailThread.workspace_id == ctx.workspace_id
        )
    )
    thread = th_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Email thread not found")

    msg_res = await db.execute(
        select(EmailMessage).where(
            EmailMessage.id == payload.inbound_message_id,
            EmailMessage.workspace_id == ctx.workspace_id
        )
    )
    msg = msg_res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Inbound message not found")

    lead_res = await db.execute(
        select(CRMLead).where(
            CRMLead.id == thread.lead_id,
            CRMLead.workspace_id == ctx.workspace_id
        )
    )
    lead = lead_res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Associated lead not found")

    # Classify intent first
    classification = await IntentClassifier.classify_reply(
        text=msg.body_text,
        subject=msg.subject,
        workspace_id=ctx.workspace_id
    )

    # Generate reply
    return await GroundedReplyAgent.generate_grounded_reply(
        workspace_id=ctx.workspace_id,
        lead=lead,
        thread=thread,
        inbound_message=msg,
        classification=classification,
        db=db
    )
