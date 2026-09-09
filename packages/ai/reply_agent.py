import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMLead
from packages.common.models.email import EmailThread, EmailMessage
from packages.common.models.knowledge import BusinessProfile, KnowledgeChunk, KnowledgeDocument
from packages.common.models.campaign import ConversationEvent
from packages.ai.schemas import InboundReplyDraft, IntentClassificationResult
from packages.ai.taxonomy import IntentType, INTENT_DEFINITIONS
from packages.ai.gateway import ModelGateway
from packages.ai.embeddings import EmbeddingGenerator

logger = logging.getLogger("codenter.ai.reply_agent")

class GroundedReplyAgent:
    """
    Autonomous Grounded Reply Agent for inbound prospect responses.
    Strictly answers inquiries with verified knowledge base citations.
    Only auto-sends if confidence >= 0.85 and intent is safe; otherwise routes to Human Review.
    """
    @classmethod
    async def generate_grounded_reply(
        cls,
        workspace_id: str,
        lead: CRMLead,
        thread: EmailThread,
        inbound_message: EmailMessage,
        classification: IntentClassificationResult,
        db: AsyncSession,
        gateway: Optional[ModelGateway] = None,
        prompt_version: str = "v1.0-grounded-reply"
    ) -> InboundReplyDraft:
        try:
            intent_enum = IntentType(classification.intent)
        except ValueError:
            intent_enum = IntentType.PRODUCT_QUESTION

        metadata = INTENT_DEFINITIONS.get(intent_enum)

        # 1. Check if intent permits auto-reply
        if not metadata or not metadata.can_auto_reply or classification.requires_human_review:
            logger.info(f"Intent {classification.intent} requires human review. Suppressing auto-reply.")
            return InboundReplyDraft(
                subject=f"Re: {thread.subject}",
                body="[Automated reply held for human sales representative review]",
                citations=[],
                confidence=classification.confidence,
                requires_human_review=True,
                reasoning=f"Intent '{classification.intent}' is routed to Human Review Inbox by policy."
            )

        # 2. Fetch BusinessProfile
        bp_res = await db.execute(
            select(BusinessProfile).where(
                BusinessProfile.workspace_id == workspace_id,
                BusinessProfile.is_active == True
            ).order_by(BusinessProfile.version.desc())
        )
        business_profile = bp_res.scalars().first()
        company_name = business_profile.company_name if business_profile else "Our Team"

        # 3. Retrieve relevant knowledge chunks for the prospect inquiry
        inquiry_text = f"{inbound_message.subject} {inbound_message.body_text}"
        query_emb = await EmbeddingGenerator.get_embedding(inquiry_text)

        chunks_res = await db.execute(
            select(KnowledgeChunk, KnowledgeDocument.url)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeChunk.workspace_id == workspace_id)
        )
        all_chunks = chunks_res.all()

        scored = []
        for chk, doc_url in all_chunks:
            sim = EmbeddingGenerator.cosine_similarity(query_emb, chk.embedding) if chk.embedding else 0.5
            scored.append((chk, doc_url, sim))
        scored.sort(key=lambda x: x[2], reverse=True)
        top_chunks = scored[:3]

        citations = [doc_url for _, doc_url, _ in top_chunks]
        chunk_ids = [chk.id for chk, _, _ in top_chunks]

        # 4. Construct Grounded Reply Prompt
        system_prompt = (
            f"You are a helpful, professional Sales Development Representative representing {company_name}.\n"
            f"DIRECTIVES:\n"
            f"1. Answer the prospect's inquiry directly, accurately, and concisely (<100 words).\n"
            f"2. Only quote verified facts from the provided knowledge chunks.\n"
            f"3. Include relevant source citation URLs.\n"
            f"4. Propose a clear, low-friction next step (e.g. 15-minute call or sending calendar link).\n"
            f"5. If information cannot be verified, set requires_human_review = True."
        )

        user_prompt_lines = [
            f"Prospect Name: {lead.first_name or 'there'}",
            f"Company: {lead.company_name or 'their team'}",
            f"Classified Intent: {classification.intent}",
            f"Prospect Inbound Message:\n{inbound_message.body_text}",
            "",
            "VERIFIED KNOWLEDGE CHUNKS:"
        ]
        for idx, (chk, doc_url, _) in enumerate(top_chunks, 1):
            user_prompt_lines.append(f"[{idx} | {doc_url}]: {chk.content[:350]}")

        gw = gateway or ModelGateway()
        draft, telemetry = await gw.generate_structured(
            system_prompt=system_prompt,
            user_prompt="\n".join(user_prompt_lines),
            schema=InboundReplyDraft,
            workspace_id=workspace_id,
            prompt_version=prompt_version
        )

        # Enforce Grounding & Confidence Thresholds
        if draft.confidence < 0.85 or classification.confidence < 0.85:
            draft.requires_human_review = True

        if not draft.citations and citations:
            draft.citations = citations[:2]

        # 5. Record Immutable 5-Question Audit Trail
        audit_event = ConversationEvent(
            workspace_id=workspace_id,
            lead_id=lead.id,
            campaign_id=thread.campaign_id,
            event_type="INBOUND_REPLY_GENERATION",
            rule_matched="GROUNDED_INBOUND_REPLY_POLICY",
            model_version=telemetry.model,
            prompt_version=prompt_version,
            knowledge_chunk_ids=chunk_ids,
            previous_state=thread.status.value,
            new_state="PENDING_AUTO_REPLY" if not draft.requires_human_review else "HUMAN_REVIEW_INBOX",
            payload={
                "intent": classification.intent,
                "confidence": draft.confidence,
                "requires_human_review": draft.requires_human_review,
                "citations": draft.citations,
                "reasoning": draft.reasoning,
                "cost_usd": telemetry.cost_usd
            }
        )
        db.add(audit_event)
        await db.commit()

        return draft
