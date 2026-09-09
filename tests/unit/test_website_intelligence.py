import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.website_intelligence.normalizer import URLNormalizer
from packages.website_intelligence.robots import RobotsParser
from packages.website_intelligence.cleaner import ContentCleaner
from packages.website_intelligence.crawler_service import WebsiteCrawlerService
from packages.common.models.knowledge import BusinessProfile, KnowledgeDocument, KnowledgeChunk, WebsiteScan, ScanStatus
from packages.common.models.workspace import Workspace
from packages.ai.embeddings import EmbeddingGenerator

def test_url_normalizer():
    raw_url = "HTTP://Www.Example.COM:80/products/?utm_source=google&utm_medium=cpc&sort=asc#features"
    normalized = URLNormalizer.normalize(raw_url)
    assert normalized == "http://www.example.com/products?sort=asc"
    assert "utm_source" not in normalized
    assert "features" not in normalized

    assert URLNormalizer.is_same_domain("https://example.com/page", "http://www.example.com/other") is True
    assert URLNormalizer.is_same_domain("https://example.com", "https://other.com") is False

def test_content_cleaner_strips_boilerplate():
    html = """
    <!DOCTYPE html>
    <html>
      <head><title>Acme AI - Next Gen SDR</title><script>alert('malicious')</script></head>
      <body>
        <header><nav><a href="/home">Home</a></nav></header>
        <div id="cookie-banner">Please accept cookies</div>
        <h1>AI Powered Sales Development</h1>
        <p>Codenter AI SDR autonomously engages prospects and books meetings.</p>
        <h2>Key Benefits</h2>
        <ul>
          <li>Reduce customer acquisition cost by 40%</li>
          <li>Increase sales team pipeline velocity</li>
        </ul>
        <footer>Copyright 2026 Acme</footer>
      </body>
    </html>
    """
    cleaned = ContentCleaner.clean_html(html)
    assert cleaned.title == "Acme AI - Next Gen SDR"
    assert "AI Powered Sales Development" in cleaned.text
    assert "Reduce customer acquisition cost by 40%" in cleaned.text
    assert "alert('malicious')" not in cleaned.text
    assert "Please accept cookies" not in cleaned.text
    assert "Copyright 2026" not in cleaned.text
    assert len(cleaned.content_hash) == 64

@pytest.mark.asyncio
async def test_crawler_service_and_grounded_rag(db_session: AsyncSession):
    # 1. Create test workspace
    ws = Workspace(name="Test Grounding Corp", domain="testcorp.com", settings={})
    db_session.add(ws)
    await db_session.flush()

    # 2. Create scan record
    scan = WebsiteScan(workspace_id=ws.id, url="https://mockcompany.com", status=ScanStatus.PENDING)
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    # 3. Define Mock HTTP Transport for multi-page crawl
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str == "https://mockcompany.com/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /admin\n")
        elif url_str in ("https://mockcompany.com/sitemap.xml", "https://mockcompany.com/sitemap_index.xml"):
            sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>https://mockcompany.com/product</loc></url>
              <url><loc>https://mockcompany.com/pricing</loc></url>
              <url><loc>https://mockcompany.com/refund-policy</loc></url>
              <url><loc>https://mockcompany.com/blocked-page</loc></url>
            </urlset>"""
            return httpx.Response(200, text=sitemap_xml)
        elif url_str == "https://mockcompany.com/":
            return httpx.Response(200, text="<html><head><title>MockCompany AI</title></head><body><h1>Enterprise AI Agents</h1><p>We build autonomous sales agents.</p></body></html>")
        elif url_str == "https://mockcompany.com/product":
            return httpx.Response(200, text="<html><head><title>Product</title></head><body><h2>Autonomous Sales Orchestration</h2><p>- Real-time CRM Sync with HubSpot</p><p>- Anti-spam pacing jitter protection</p></body></html>")
        elif url_str == "https://mockcompany.com/pricing":
            return httpx.Response(200, text="<html><head><title>Pricing</title></head><body><h1>Plans and Pricing</h1><p>Starter Tier is $49/mo. Enterprise Tier is $199/mo.</p></body></html>")
        elif url_str == "https://mockcompany.com/refund-policy":
            return httpx.Response(200, text="<html><head><title>Refund Policy</title></head><body><h1>Refund Terms</h1><p>Our refund policy guarantees 100% full money back within 30 days of purchase for any unsatisfied customers.</p></body></html>")
        elif url_str == "https://mockcompany.com/blocked-page":
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport, base_url="https://mockcompany.com")

    # 4. Execute Crawler Workflow
    completed_scan = await WebsiteCrawlerService.run_scan(
        workspace_id=ws.id,
        scan_id=scan.id,
        base_url="https://mockcompany.com",
        db=db_session,
        mock_client=mock_client
    )

    # 5. Verify Scan Status & Partial Failure Handling
    # The blocked-page failed, so status must be PARTIAL_FAILURE
    assert completed_scan.status == ScanStatus.PARTIAL_FAILURE
    assert completed_scan.pages_crawled >= 4
    assert completed_scan.pages_failed == 1

    # 6. Verify KnowledgeDocument and KnowledgeChunk populated
    docs_res = await db_session.execute(select(KnowledgeDocument).where(KnowledgeDocument.workspace_id == ws.id))
    docs = docs_res.scalars().all()
    assert len(docs) >= 4

    chunks_res = await db_session.execute(select(KnowledgeChunk).where(KnowledgeChunk.workspace_id == ws.id))
    chunks = chunks_res.scalars().all()
    assert len(chunks) >= 4

    # 7. Verify BusinessProfile extracted
    prof_res = await db_session.execute(select(BusinessProfile).where(BusinessProfile.workspace_id == ws.id))
    profile = prof_res.scalar_one()
    assert profile.company_name == "MockCompany AI"
    assert profile.pricing is not None
    assert profile.pricing["model"] == "PUBLIC_TIERS"
    assert profile.is_active is True

    # 8. Verify Grounded Vector Search for "What is the refund policy?"
    query = "What is the refund policy?"
    query_emb = await EmbeddingGenerator.get_embedding(query)

    scored_chunks = []
    for c in chunks:
        sim = EmbeddingGenerator.cosine_similarity(query_emb, c.embedding)
        scored_chunks.append((c, sim))

    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    top_chunk, top_score = scored_chunks[0]

    # Must retrieve the refund terms chunk
    assert "refund policy guarantees 100% full money back" in top_chunk.content
    assert top_chunk.metadata_json["source_url"] == "https://mockcompany.com/refund-policy"
