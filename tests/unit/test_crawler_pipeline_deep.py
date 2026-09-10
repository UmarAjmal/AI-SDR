import pytest
from datetime import datetime, timezone
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

def test_null_byte_sanitization_prevents_postgresql_error():
    """
    Verify that 0x00 null bytes in web HTML, titles, text, and metadata
    are strictly stripped before persisting into PostgreSQL UTF-8 text columns.
    """
    from packages.website_intelligence.crawler_service import _clean_pg_text, _clean_pg_data

    dirty_html = "<html><head><title>Corrupted\x00Title</title></head><body><h1>Heading\x00One</h1><p>Text with null\x00byte.</p></body></html>"
    cleaned = ContentCleaner.clean_html(dirty_html, base_url="https://store.myshopify.com/product\x00bad")

    assert "\x00" not in cleaned.title
    assert "\x00" not in cleaned.text
    assert "\x00" not in cleaned.headings[0]["text"]
    assert cleaned.title == "CorruptedTitle"
    assert "Text with nullbyte." in cleaned.text

    # Test chunking sanitization
    chunks = SemanticChunker.chunk_text(
        text="Chunk with \x00 null byte content",
        source_url="https://site.com/item\x001",
        title="Title\x00Test"
    )
    assert len(chunks) == 1
    assert "\x00" not in chunks[0].content
    assert "\x00" not in chunks[0].metadata["source_url"]
    assert "\x00" not in chunks[0].metadata["title"]

    # Test nested dict/list sanitization
    dirty_data = {
        "title\x00": "Clean\x00Me",
        "nested": [{"desc": "Null\x00Found", "num": 123}],
        "none_val": None
    }
    cleaned_dict = _clean_pg_data(dirty_data)
    assert "title" in cleaned_dict
    assert cleaned_dict["title"] == "CleanMe"
    assert cleaned_dict["nested"][0]["desc"] == "NullFound"
    assert cleaned_dict["nested"][0]["num"] == 123
    assert _clean_pg_text("Safe\x00String") == "SafeString"

def test_stratified_categorical_crawl_budgeting_prevents_product_starvation():
    """
    Section 4.1 Rule 20: Tests that when hundreds of product URLs are discovered,
    the stratified budgeting algorithm strictly guarantees slots for high-value
    Policies, FAQs, Contact, About, and Collections without starvation.
    """
    from packages.website_intelligence.sitemap import SitemapCrawler

    mock_discovered = [("https://example.com/", 120)]

    # 400 Product URLs (score 100)
    for i in range(400):
        mock_discovered.append((f"https://example.com/products/item-{i}", 100))

    # 15 Collection URLs (score 95)
    for i in range(15):
        mock_discovered.append((f"https://example.com/collections/category-{i}", 95))

    # 3 About URLs (score 80)
    mock_discovered.append(("https://example.com/pages/about-us", 80))
    mock_discovered.append(("https://example.com/pages/our-story", 75))

    # 2 Contact URLs (score 70)
    mock_discovered.append(("https://example.com/pages/contact-us", 70))

    # 4 FAQ URLs (score 75)
    mock_discovered.append(("https://example.com/pages/faqs", 75))
    mock_discovered.append(("https://example.com/pages/help", 70))

    # 5 Policy URLs (score 60)
    mock_discovered.append(("https://example.com/policies/refund-policy", 60))
    mock_discovered.append(("https://example.com/policies/shipping-policy", 60))
    mock_discovered.append(("https://example.com/policies/terms-of-service", 55))

    # Run stratified budgeting with max budget = 50
    selected = SitemapCrawler.stratify_urls(mock_discovered, max_budget=50)

    # Assert that all critical business pages are included and NOT starved by 400 product URLs
    assert "https://example.com/" in selected
    assert "https://example.com/pages/about-us" in selected
    assert "https://example.com/pages/contact-us" in selected
    assert "https://example.com/pages/faqs" in selected
    assert "https://example.com/policies/refund-policy" in selected
    assert "https://example.com/policies/shipping-policy" in selected
    assert "https://example.com/policies/terms-of-service" in selected

    # Assert collections are represented
    collection_count = len([u for u in selected if "/collections/" in u])
    assert 5 <= collection_count <= 12

    # Assert products are represented without exceeding quota
    product_count = len([u for u in selected if "/products/" in u])
    assert 10 <= product_count <= 35

    assert len(selected) <= 50

def test_json_ld_schema_structured_extraction_and_provenance():
    """
    Section 4.1 Rule 26 & 28: Tests that JSON-LD Product, Organization, and FAQ schemas
    are extracted with exact provenance, prices, currencies, contact details, and confidence.
    """
    html_with_json_ld = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Embroidered Kurti | Manto</title>
        <meta property="og:site_name" content="Manto" />
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Product",
                    "name": "Iqbal Poetry Embroidered Kurti",
                    "sku": "MNT-1092",
                    "category": "Apparel > Kurtis",
                    "description": "Premium lawn kurti featuring handcrafted Allama Iqbal calligraphy.",
                    "offers": {
                        "@type": "Offer",
                        "price": "4950",
                        "priceCurrency": "PKR",
                        "availability": "https://schema.org/InStock"
                    }
                },
                {
                    "@type": "Organization",
                    "name": "Manto Apparel Pvt Ltd",
                    "legalName": "Manto Design House Pvt Ltd",
                    "telephone": "+92 300 1234567",
                    "email": "care@shopmanto.com",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "Gulberg III",
                        "addressLocality": "Lahore",
                        "addressCountry": "PK"
                    }
                },
                {
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": "What is the return and exchange window?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": "We offer a hassle-free 7-day exchange window for all unworn items."
                            }
                        }
                    ]
                }
            ]
        }
        </script>
    </head>
    <body>
        <h1>Iqbal Poetry Embroidered Kurti</h1>
        <p>Price: Rs. 4,950</p>
    </body>
    </html>
    """

    cleaned = ContentCleaner.clean_html(html_with_json_ld, base_url="https://www.shopmanto.com/products/kurti")
    assert cleaned.site_name == "Manto"
    assert len(cleaned.json_ld_data) >= 3

    page = FetchedPage(
        url="https://www.shopmanto.com/products/kurti",
        status_code=200,
        html=html_with_json_ld,
        cleaned=cleaned
    )

    extracted = BusinessExtractor.extract_from_pages([page])

    # Assert Company Name extracted from og:site_name
    assert extracted["company_name"] == "Manto"
    assert extracted["legal_name"] == "Manto Design House Pvt Ltd"

    # Assert Product offering extracted from JSON-LD
    assert any(o["title"] == "Iqbal Poetry Embroidered Kurti" for o in extracted["offerings"])
    matching_offering = next(o for o in extracted["offerings"] if o["title"] == "Iqbal Poetry Embroidered Kurti")
    assert matching_offering["price"] == "PKR 4950"
    assert matching_offering["sku"] == "MNT-1092"
    assert matching_offering["source_url"] == "https://www.shopmanto.com/products/kurti"

    # Assert Organization contact info extracted
    assert "+92 300 1234567" in extracted["contact_info"]["phones"]
    assert "care@shopmanto.com" in extracted["contact_info"]["emails"]
    assert any("Lahore" in addr for addr in extracted["contact_info"]["addresses"])

    # Assert FAQ extracted
    assert any("return and exchange window" in f["question"].lower() for f in extracted["faqs"])

    # Assert Structured Facts provenance
    facts = extracted["structured_facts"]
    assert any(f["fact_type"] == "OFFERING" and f["source_url"] == "https://www.shopmanto.com/products/kurti" for f in facts)
    assert any(f["fact_type"] == "CONTACT" for f in facts)
    assert any(f["fact_type"] == "FAQ" for f in facts)

def test_brand_identity_and_policy_extraction():
    """
    Tests brand token domain matching and comprehensive policy extraction.
    """
    policy_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Refund and Exchange Policy – Zimal</title>
    </head>
    <body>
        <h1>Exchange Policy</h1>
        <p>Exchange requests must be submitted within 7 days of delivery.</p>
        <p>Items must be unworn and in original condition with tags intact.</p>
        <h2>Shipping and Delivery Information</h2>
        <p>Standard delivery takes 3 to 5 working days nationwide across Pakistan.</p>
        <p>Free shipping on all orders above Rs. 3,000.</p>
    </body>
    </html>
    """
    cleaned = ContentCleaner.clean_html(policy_html, base_url="https://zimal.com.pk/pages/exchange-policy")
    page = FetchedPage(
        url="https://zimal.com.pk/pages/exchange-policy",
        status_code=200,
        html=policy_html,
        cleaned=cleaned
    )

    extracted = BusinessExtractor.extract_from_pages([page])
    assert extracted["company_name"] == "Zimal"

    # Verify policies extracted
    policies = extracted["policies"]
    assert len(policies) >= 2
    assert any("within 7 days" in p["policy"].lower() for p in policies)
    assert any("3 to 5 working days" in p["policy"].lower() for p in policies)

    # Verify pricing detection from free shipping rule
    assert extracted["pricing"]["model"] in ("PUBLIC_TIERS", "PUBLIC_CATALOG_PRICING")
    assert extracted["pricing"]["currency"] == "PKR"

