import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.common.models.knowledge import BusinessProfile, KnowledgeDocument, KnowledgeChunk
from packages.common.models.crm import CRMLead, LeadEnrichment
from packages.common.models.campaign import Campaign, CampaignStep
from packages.ai.context_builder import BoundedContextBuilder, MAX_PROMPT_TOKENS
from packages.ai.embeddings import EmbeddingGenerator

@pytest.mark.asyncio
async def test_bounded_context_assembly_and_token_cap(db_session: AsyncSession):
    workspace_id = "ws-ctx-test"

    # 1. Setup BusinessProfile
    bp = BusinessProfile(
        workspace_id=workspace_id,
        company_name="Codenter AI",
        description="Autonomous sales development platform.",
        offerings=[{"name": "AI SDR Agent", "tier": "Growth"}],
        value_propositions=["Scale pipeline 3.2x with zero hallucination"],
        proof=["Enterprise client achieved 3.2x qualified pipeline in 45 days"],
        claims_policy={"prohibited_claims": ["100% guarantee", "free forever"]}
    )
    db_session.add(bp)

    # 2. Setup Knowledge Document & 4 Chunks
    doc = KnowledgeDocument(
        workspace_id=workspace_id,
        url="https://codenter.ai/case-studies",
        title="Enterprise Case Studies",
        content_hash="hash-12345",
        raw_text="Full text"
    )
    db_session.add(doc)
    await db_session.flush()

    chunks_data = [
        "Chunk 1: Fintech teams scale pipeline by 4x using autonomous outbound.",
        "Chunk 2: Healthcare HIPAA compliance guarantees for SDR data processing.",
        "Chunk 3: SaaS sales engineering playbooks for pipeline velocity.",
        "Chunk 4: Retail e-commerce discount strategies."
    ]

    for idx, text in enumerate(chunks_data):
        emb = await EmbeddingGenerator.get_embedding(text)
        chk = KnowledgeChunk(
            workspace_id=workspace_id,
            document_id=doc.id,
            chunk_index=idx,
            content=text,
            token_count=len(text) // 4,
            embedding=emb
        )
        db_session.add(chk)

    # 3. Setup Lead & Step
    lead = CRMLead(
        workspace_id=workspace_id,
        first_name="Marcus",
        last_name="Vance",
        email="marcus@saascorp.io",
        job_title="VP of Sales",
        company_name="SaaSCorp",
        industry="SaaS",
        location="New York, NY"
    )
    db_session.add(lead)
    await db_session.flush()

    enr = LeadEnrichment(
        workspace_id=workspace_id,
        lead_id=lead.id,
        role_summary="Oversees 40 BDRs focused on mid-market software sales.",
        detected_technologies=["Salesforce", "Outreach.io"],
        signals_json=["Hiring 10 SDRs this quarter"]
    )
    db_session.add(enr)

    step = CampaignStep(
        campaign_id="camp-dummy",
        step_number=1,
        delay_days=0,
        delay_hours=0,
        prompt_instructions="Focus on SaaS sales velocity and ROI proof points."
    )

    await db_session.commit()

    # 4. Assemble Bounded Context
    pkg = await BoundedContextBuilder.build_outbound_context(
        workspace_id=workspace_id,
        lead=lead,
        step=step,
        db=db_session
    )

    # Assert bounded tokens ceiling
    assert pkg.estimated_tokens <= MAX_PROMPT_TOKENS
    assert len(pkg.retrieved_chunks) <= 3
    assert len(pkg.knowledge_chunk_ids) <= 3

    # Assert prompt contains grounded profile and lead facts
    assert "Codenter AI" in pkg.system_prompt
    assert "Marcus" in pkg.user_prompt
    assert "SaaSCorp" in pkg.user_prompt
    assert "VP of Sales" in pkg.user_prompt
    assert "Hiring 10 SDRs" in pkg.user_prompt
    assert "100% guarantee" in pkg.prohibited_claims

    # Assert SaaS chunk was retrieved in top chunks
    retrieved_content = " ".join([c.content for c in pkg.retrieved_chunks])
    assert "SaaS" in retrieved_content
