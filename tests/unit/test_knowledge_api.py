import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_knowledge_and_scan_endpoints(client: AsyncClient, db_session: AsyncSession):
    # 1. Register user & workspace
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": "crawler.admin@enterprise.com",
        "password": "StrongPassword123!",
        "workspace_name": "Enterprise AI Lab"
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Trigger website scan
    scan_res = await client.post(
        "/api/v1/website-scans",
        json={"url": "https://example.com"},
        headers=headers
    )
    assert scan_res.status_code == 202
    scan_data = scan_res.json()
    assert scan_data["status"] == "PENDING"
    assert scan_data["url"] == "https://example.com"
    scan_id = scan_data["id"]

    # 3. Check scan progress
    status_res = await client.get(f"/api/v1/website-scans/{scan_id}", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["id"] == scan_id

    # 4. Attempt to get business profile before scan completes (should return 404)
    prof_res = await client.get("/api/v1/business-profile", headers=headers)
    assert prof_res.status_code == 404

    # 5. Populate profile directly to test GET, PUT, and search
    from packages.common.models.knowledge import BusinessProfile, KnowledgeDocument, KnowledgeChunk
    from packages.ai.embeddings import EmbeddingGenerator
    from sqlalchemy import select
    from packages.common.models.user import User
    from packages.common.models.workspace import WorkspaceMember

    u_res = await db_session.execute(select(User).where(User.email == "crawler.admin@enterprise.com"))
    user = u_res.scalar_one()
    m_res = await db_session.execute(select(WorkspaceMember).where(WorkspaceMember.user_id == user.id))
    member = m_res.scalar_one()
    ws_id = member.workspace_id

    profile = BusinessProfile(
        workspace_id=ws_id,
        company_name="Enterprise AI Lab",
        description="Initial AI description",
        offerings=[{"title": "Agentic Platform"}],
        value_propositions=[],
        industries=["Fintech"],
        icp_hints={},
        pricing={"model": "CONTACT_SALES"},
        features=[],
        faqs=[],
        proof=[],
        brand_voice={},
        claims_policy={},
        ctas=[],
        version=1,
        is_active=True
    )
    db_session.add(profile)

    doc = KnowledgeDocument(
        workspace_id=ws_id,
        url="https://enterprise.com/pricing",
        title="Enterprise Pricing",
        content_hash="hash123",
        source_type="WEBSITE",
        raw_text="Enterprise pricing starts at $99 per seat per month."
    )
    db_session.add(doc)
    await db_session.flush()

    emb = await EmbeddingGenerator.get_embedding("Enterprise pricing starts at $99 per seat per month.")
    chunk = KnowledgeChunk(
        workspace_id=ws_id,
        document_id=doc.id,
        chunk_index=0,
        content="Enterprise pricing starts at $99 per seat per month.",
        token_count=12,
        embedding=emb,
        metadata_json={"source_url": doc.url}
    )
    db_session.add(chunk)
    await db_session.commit()

    # 6. Verify GET /api/v1/business-profile succeeds
    prof_get = await client.get("/api/v1/business-profile", headers=headers)
    assert prof_get.status_code == 200
    assert prof_get.json()["company_name"] == "Enterprise AI Lab"
    assert prof_get.json()["version"] == 1

    # 7. Update profile via PUT /api/v1/business-profile
    put_res = await client.put(
        "/api/v1/business-profile",
        json={
            "company_name": "Enterprise AI Lab Global",
            "description": "Updated description with proven ROI",
            "industries": ["Fintech", "Healthcare"]
        },
        headers=headers
    )
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["company_name"] == "Enterprise AI Lab Global"
    assert updated_data["description"] == "Updated description with proven ROI"
    assert "Healthcare" in updated_data["industries"]
    assert updated_data["version"] == 2

    # 8. Test /api/v1/knowledge/search
    search_res = await client.post(
        "/api/v1/knowledge/search?query=What+is+the+enterprise+pricing%3F&limit=3",
        headers=headers
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert "Enterprise pricing starts at $99" in results[0]["content"]
    assert results[0]["source_url"] == "https://enterprise.com/pricing"

