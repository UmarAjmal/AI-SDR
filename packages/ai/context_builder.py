import logging
from typing import Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.knowledge import BusinessProfile, KnowledgeChunk, KnowledgeDocument
from packages.common.models.crm import CRMLead, LeadEnrichment
from packages.common.models.campaign import CampaignStep
from packages.common.models.email import EmailMessage
from packages.ai.embeddings import EmbeddingGenerator

logger = logging.getLogger("codenter.ai.context_builder")

MAX_PROMPT_TOKENS = 3000

@dataclass
class RetrievedChunk:
    chunk_id: str
    content: str
    source_url: str
    similarity_score: float

@dataclass
class BoundedContextPackage:
    system_prompt: str
    user_prompt: str
    estimated_tokens: int
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    knowledge_chunk_ids: list[str] = field(default_factory=list)
    claims_policy: dict = field(default_factory=dict)
    prohibited_claims: list[str] = field(default_factory=list)

class BoundedContextBuilder:
    """
    Constructs a high-relevance, zero-hallucination bounded context prompt package:
    1. Retrieves top 2-3 knowledge_chunks via vector cosine similarity.
    2. Injects verified Business Profile, lead details, enrichment signals, and sequence goals.
    3. Strictly enforces the 3,000 token context window boundary.
    """
    @classmethod
    async def build_outbound_context(
        cls,
        workspace_id: str,
        lead: CRMLead,
        step: Optional[CampaignStep] = None,
        db: Optional[AsyncSession] = None,
        custom_instructions: Optional[str] = None,
        thread_messages: Optional[list[EmailMessage]] = None
    ) -> BoundedContextPackage:
        if db is None:
            raise ValueError("AsyncSession 'db' is required for context assembly")

        # 1. Fetch Active BusinessProfile
        bp_res = await db.execute(
            select(BusinessProfile).where(
                BusinessProfile.workspace_id == workspace_id,
                BusinessProfile.is_active == True
            ).order_by(BusinessProfile.version.desc())
        )
        business_profile = bp_res.scalars().first()

        company_name = business_profile.company_name if business_profile else "Our Team"
        description = business_profile.description if business_profile else ""
        offerings = (business_profile.offerings if business_profile else []) or []
        value_props = (business_profile.value_propositions if business_profile else []) or []
        proof_points = (business_profile.proof if business_profile else []) or []
        claims_policy = (business_profile.claims_policy if business_profile else {}) or {}
        prohibited = claims_policy.get("prohibited_claims", [
            "100% guarantee", "unlimited free trial", "99.999% revenue lift", "free setup"
        ])

        # 2. Semantic Search for Top 2-3 Knowledge Chunks
        query_text = f"{lead.company_name or ''} {lead.industry or ''} {lead.job_title or ''} {step.prompt_instructions if step else ''}"
        query_embedding = await EmbeddingGenerator.get_embedding(query_text)

        chunks_res = await db.execute(
            select(KnowledgeChunk, KnowledgeDocument.url)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeChunk.workspace_id == workspace_id)
        )
        all_chunks = chunks_res.all()

        scored_chunks: list[RetrievedChunk] = []
        for chunk_model, doc_url in all_chunks:
            if chunk_model.embedding:
                score = EmbeddingGenerator.cosine_similarity(query_embedding, chunk_model.embedding)
            else:
                score = 0.5
            scored_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_model.id,
                    content=chunk_model.content,
                    source_url=doc_url,
                    similarity_score=score
                )
            )

        scored_chunks.sort(key=lambda c: c.similarity_score, reverse=True)
        top_chunks = scored_chunks[:3]
        chunk_ids = [c.chunk_id for c in top_chunks]

        # 3. Fetch Lead Enrichment if present
        enr_res = await db.execute(
            select(LeadEnrichment).where(
                LeadEnrichment.lead_id == lead.id,
                LeadEnrichment.workspace_id == workspace_id
            )
        )
        enrichment = enr_res.scalar_one_or_none()

        # 4. Construct System Prompt (Strict Grounding Rules)
        system_prompt = (
            f"You are a premier Enterprise AI Sales Development Representative (SDR) representing {company_name}.\n"
            f"CORE DIRECTIVES:\n"
            f"1. ZERO HALLUCINATION: You must ONLY cite verifiable facts, metrics, and customer outcomes explicitly present in the provided context.\n"
            f"2. NO FAKE RESEARCH: Do NOT reference LinkedIn posts, tweets, or personal statements unless an exact URL is provided in the verified lead signals.\n"
            f"3. PROHIBITED CLAIMS: Never make claims or guarantees in the prohibited list: {prohibited}.\n"
            f"4. Keep outreach concise, value-oriented, and conversational (<120 words).\n"
            f"5. Output must strictly conform to the required JSON schema with a clear confidence score (0.0 to 1.0) and recommended action (SEND or HUMAN_REVIEW)."
        )

        # 5. Construct User Prompt
        user_prompt_lines = [
            f"### COMPANY PROFILE: {company_name}",
            f"Description: {description}",
            f"Key Offerings: {offerings[:3]}",
            f"Value Propositions: {value_props[:3]}",
            f"Verified Proof Points: {proof_points[:3]}",
            "",
            f"### TARGET PROSPECT DETAILS",
            f"Name: {lead.first_name or 'there'} {lead.last_name or ''}".strip(),
            f"Title: {lead.job_title or 'Leader'}",
            f"Company: {lead.company_name or 'Your Company'}",
            f"Industry: {lead.industry or 'Technology'}",
            f"Location: {lead.location or 'Global'}"
        ]

        if enrichment:
            if enrichment.role_summary:
                user_prompt_lines.append(f"Role Context: {enrichment.role_summary}")
            if enrichment.detected_technologies:
                user_prompt_lines.append(f"Technologies: {enrichment.detected_technologies[:4]}")
            if enrichment.signals_json:
                user_prompt_lines.append(f"Verified Signals: {enrichment.signals_json[:2]}")

        if step:
            user_prompt_lines.append("")
            user_prompt_lines.append(f"### CAMPAIGN SEQUENCE OBJECTIVE (Step {step.step_number})")
            if step.prompt_instructions:
                user_prompt_lines.append(f"Instructions: {step.prompt_instructions}")
            if step.template_config_json:
                user_prompt_lines.append(f"Template Reference: {step.template_config_json}")

        if custom_instructions:
            user_prompt_lines.append(f"Additional Guidance: {custom_instructions}")

        if thread_messages:
            user_prompt_lines.append("")
            user_prompt_lines.append("### PRIOR THREAD HISTORY")
            for msg in thread_messages[-3:]:
                user_prompt_lines.append(f"[{msg.direction.value}] {msg.subject}: {msg.body_text[:200]}")

        user_prompt_lines.append("")
        user_prompt_lines.append("### VERIFIED GROUNDING KNOWLEDGE CHUNKS (Reference strictly)")
        for idx, chunk in enumerate(top_chunks, 1):
            user_prompt_lines.append(f"[Chunk {idx} | Source: {chunk.source_url}]: {chunk.content[:400]}")

        user_prompt = "\n".join(user_prompt_lines)

        # 6. Check Token Limit Boundary
        estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
        if estimated_tokens > MAX_PROMPT_TOKENS:
            logger.warning(f"Context exceeds {MAX_PROMPT_TOKENS} tokens ({estimated_tokens}); truncating user prompt.")
            char_budget = MAX_PROMPT_TOKENS * 4 - len(system_prompt)
            user_prompt = user_prompt[:char_budget] + "\n[Context bounded for safety]"
            estimated_tokens = MAX_PROMPT_TOKENS

        return BoundedContextPackage(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            estimated_tokens=estimated_tokens,
            retrieved_chunks=top_chunks,
            knowledge_chunk_ids=chunk_ids,
            claims_policy=claims_policy,
            prohibited_claims=prohibited
        )
