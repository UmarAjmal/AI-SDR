import pytest
from packages.website_intelligence.cleaner import ContentCleaner
from packages.website_intelligence.sitemap import SitemapCrawler
from packages.website_intelligence.fetcher import FetchedPage
from packages.ai.extractors.business_extractor import BusinessExtractor
from packages.ai.chunking import SemanticChunker

def test_table_preservation_and_headings_hierarchy():
    html = """
    <html>
      <head><title>Pricing Matrix | Acme AI</title></head>
      <body>
        <h1>Pricing Plans</h1>
        <h2>Feature Breakdown</h2>
        <table>
          <tr><th>Tier</th><th>Price</th><th>Users</th></tr>
          <tr><td>Starter</td><td>$49/mo</td><td>1 User</td></tr>
          <tr><td>Pro</td><td>$149/mo</td><td>5 Users</td></tr>
        </table>
        <p>Contact support for enterprise quotes.</p>
      </body>
    </html>
    """
    cleaned = ContentCleaner.clean_html(html, base_url="https://acme.ai/pricing")
    assert cleaned.page_type == "PRICING"
    assert cleaned.business_topic == "PRICING_MODEL"
    assert len(cleaned.headings) >= 2
    assert cleaned.headings[0]["text"] == "Pricing Plans"
    assert len(cleaned.structured_tables) == 1
    assert "| Starter | $49/mo | 1 User |" in cleaned.text

def test_page_classification_taxonomy():
    pages = [
        ("https://shop.com/", "Home", "HOME", "COMPANY_INFO"),
        ("https://shop.com/collections/summer-lawn", "Summer Lawn Catalog", "PRODUCT_CATALOG", "CORE_OFFERING"),
        ("https://shop.com/products/embroidered-shirt", "Embroidered Shirt", "PRODUCT_DETAIL", "CORE_OFFERING"),
        ("https://shop.com/pages/about-us", "Our Story & Team", "ABOUT_US", "COMPANY_INFO"),
        ("https://shop.com/pages/faqs", "Frequently Asked Questions", "FAQ", "SUPPORT_POLICY"),
        ("https://shop.com/pages/refund-policy", "Refund & Return Policy", "LEGAL_POLICY", "LEGAL_COMPLIANCE"),
        ("https://shop.com/pages/contact", "Contact Our Team", "CONTACT", "COMPANY_INFO"),
    ]
    for url, title, expected_type, expected_topic in pages:
        html = f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>Content for {title}</p></body></html>"
        cleaned = ContentCleaner.clean_html(html, base_url=url)
        assert cleaned.page_type == expected_type, f"Failed type for {url}: got {cleaned.page_type}"
        assert cleaned.business_topic == expected_topic, f"Failed topic for {url}: got {cleaned.business_topic}"

def test_structured_facts_provenance_and_quality_gate():
    p1 = FetchedPage(
        url="https://acme.ai/",
        status_code=200,
        html="<html></html>",
        cleaned=ContentCleaner.clean_html(
            "<html><head><title>Acme Software</title></head><body><h1>Enterprise AI Agents</h1><p>Contact sales at support@acme.ai or call +1-800-555-0199.</p><p>We guarantee 99.9% uptime for cloud customers.</p></body></html>",
            base_url="https://acme.ai/"
        )
    )
    p2 = FetchedPage(
        url="https://acme.ai/pricing",
        status_code=200,
        html="<html></html>",
        cleaned=ContentCleaner.clean_html(
            "<html><head><title>Pricing</title></head><body><h1>Pricing</h1><p>Starter plan starts at $99 per month.</p></body></html>",
            base_url="https://acme.ai/pricing"
        )
    )
    p3 = FetchedPage(
        url="https://acme.ai/refund-policy",
        status_code=200,
        html="<html></html>",
        cleaned=ContentCleaner.clean_html(
            "<html><head><title>Refund Policy</title></head><body><h1>Refund Policy</h1><p>We provide a 30-day money back guarantee on all software subscriptions.</p></body></html>",
            base_url="https://acme.ai/refund-policy"
        )
    )

    extracted = BusinessExtractor.extract_from_pages([p1, p2, p3])

    # Rule 26: Provenance assertions
    assert len(extracted["structured_facts"]) > 0
    for fact in extracted["structured_facts"]:
        assert "statement" in fact and len(fact["statement"]) > 0
        assert "source_url" in fact and fact["source_url"].startswith("https://")
        assert "fact_type" in fact
        assert "extracted_at" in fact
        assert fact["confidence"] >= 0.85

    # Rule 29: Quality checks
    assert extracted["confidence_score"] >= 0.85
    assert extracted["company_name"] == "Acme Software"
    assert "support@acme.ai" in extracted["contact_info"]["emails"]

def test_semantic_chunking_with_provenance_metadata():
    text = "# Product Overview\n\nOur autonomous agent performs real-time sales outreach.\n\n## Security\n\nWe enforce SOC2 compliance and zero data leakage."
    chunks = SemanticChunker.chunk_text(
        text=text,
        source_url="https://acme.ai/product",
        title="Product Overview",
        page_type="CORE_OFFERING",
        business_topic="TECHNICAL_DOC"
    )
    assert len(chunks) >= 1
    chk = chunks[0]
    assert chk.metadata["source_url"] == "https://acme.ai/product"
    assert "extraction_timestamp" in chk.metadata
    assert chk.metadata["page_type"] == "CORE_OFFERING"
    assert chk.metadata["business_topic"] == "TECHNICAL_DOC"
