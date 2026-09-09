import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from packages.common.models.crm import CRMLead, LeadEnrichment
from packages.common.models.campaign import CampaignStep, ConversationEvent
from packages.common.models.knowledge import BusinessProfile
from packages.ai.schemas import OutboundEmailDraft, ModelUsageTelemetry, RecommendedAction
from packages.ai.gateway import ModelGateway
from packages.ai.context_builder import BoundedContextBuilder
from packages.ai.verifier import ClaimVerifier

logger = logging.getLogger("codenter.ai.generation")

class AIPersonalizationService:
    """
    End-to-end service for AI email personalization, bounded context assembly,
    multi-provider model execution, claim verification, and audit logging.
    """
    @classmethod
    async def generate_outbound_draft(
        cls,
        workspace_id: str,
        lead_id: str,
        campaign_step_id: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        custom_gateway: Optional[ModelGateway] = None,
        prompt_version: str = "v2.0-grounded-outbound"
    ) -> tuple[OutboundEmailDraft, ModelUsageTelemetry, list[str]]:
        if db is None:
            raise ValueError("AsyncSession 'db' is required for AI email generation")

        # 1. Fetch Lead
        l_stmt = (
            select(CRMLead)
            .options(selectinload(CRMLead.enrichment))
            .where(CRMLead.id == lead_id, CRMLead.workspace_id == workspace_id)
        )
        l_res = await db.execute(l_stmt)
        lead = l_res.scalar_one_or_none()
        if not lead:
            raise ValueError(f"CRMLead {lead_id} not found in workspace {workspace_id}")

        # 2. Fetch CampaignStep if provided
        step = None
        if campaign_step_id:
            s_stmt = select(CampaignStep).where(CampaignStep.id == campaign_step_id)
            s_res = await db.execute(s_stmt)
            step = s_res.scalar_one_or_none()

        # 3. Assemble Bounded Context (top 2-3 chunks, <3000 tokens)
        context_pkg = await BoundedContextBuilder.build_outbound_context(
            workspace_id=workspace_id,
            lead=lead,
            step=step,
            db=db,
            custom_instructions=custom_instructions
        )

        # 4. Invoke ModelGateway
        gateway = custom_gateway or ModelGateway()
        raw_draft, telemetry = await gateway.generate_structured(
            system_prompt=context_pkg.system_prompt,
            user_prompt=context_pkg.user_prompt,
            schema=OutboundEmailDraft,
            workspace_id=workspace_id,
            prompt_version=prompt_version
        )

        # 5. Retrieve BusinessProfile for claim verification
        bp_res = await db.execute(
            select(BusinessProfile).where(
                BusinessProfile.workspace_id == workspace_id,
                BusinessProfile.is_active == True
            ).order_by(BusinessProfile.version.desc())
        )
        business_profile = bp_res.scalars().first()

        # 6. Apply Safety & Claim Verification Filter
        chunk_contents = [c.content for c in context_pkg.retrieved_chunks]
        verification = ClaimVerifier.verify_draft(
            draft=raw_draft,
            retrieved_chunk_texts=chunk_contents,
            business_profile=business_profile,
            lead_enrichment=lead.enrichment,
            prohibited_claims=context_pkg.prohibited_claims
        )

        # Synchronize verified results onto draft
        raw_draft.confidence = verification.confidence
        raw_draft.risk_flags = verification.risk_flags
        raw_draft.recommended_action = verification.recommended_action

        # 7. Record Immutable 5-Question Audit Trail
        rule_matched = (
            "GROUNDED_AI_PERSONALIZATION_PASS"
            if raw_draft.recommended_action == RecommendedAction.SEND
            else "HALLUCINATION_GATE_FLAGGED_HUMAN_REVIEW"
        )
        audit_event = ConversationEvent(
            workspace_id=workspace_id,
            lead_id=lead.id,
            campaign_id=step.campaign_id if step else None,
            event_type="AI_DRAFT_GENERATION",
            rule_matched=rule_matched,
            model_version=telemetry.model,
            prompt_version=telemetry.prompt_version,
            knowledge_chunk_ids=context_pkg.knowledge_chunk_ids,
            previous_state="GENERATING",
            new_state=raw_draft.recommended_action.value,
            payload={
                "subject": raw_draft.subject,
                "confidence": raw_draft.confidence,
                "claims_used": raw_draft.claims_used,
                "risk_flags": raw_draft.risk_flags,
                "fallback_triggered": telemetry.fallback_triggered,
                "cost_usd": telemetry.cost_usd,
                "tokens": telemetry.total_tokens
            }
        )
        db.add(audit_event)
        await db.commit()

        logger.info(
            f"Generated draft for lead {lead.id} using {telemetry.model} (Action: {raw_draft.recommended_action.value}, "
            f"Confidence: {raw_draft.confidence})"
        )

        return raw_draft, telemetry, context_pkg.knowledge_chunk_ids
