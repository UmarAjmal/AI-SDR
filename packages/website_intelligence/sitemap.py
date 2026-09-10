import urllib.parse
import xml.etree.ElementTree as ET
import httpx
import logging
from packages.website_intelligence.normalizer import URLNormalizer

logger = logging.getLogger("codenter.crawler.sitemap")

# Section 4.1 Rule 20: Prioritize high-value pages:
# home, product/service, pricing, about, industries, use cases, case studies,
# FAQ, contact, documentation and legal/policy pages.
PRIORITY_PATHS = [
    # Pricing & Commercials
    ("pricing", 110),
    ("plans", 110),
    ("cost", 105),
    ("fees", 105),
    ("subscription", 105),
    # Products & Services
    ("products", 100),
    ("product", 100),
    ("services", 100),
    ("service", 100),
    ("collections", 95),
    ("collection", 95),
    ("catalog", 95),
    ("shop", 95),
    ("store", 90),
    # Solutions & Industries & Use Cases
    ("solutions", 90),
    ("solution", 90),
    ("industries", 90),
    ("industry", 90),
    ("use-cases", 90),
    ("use-case", 90),
    ("features", 85),
    ("feature", 85),
    # Case Studies & Proof
    ("case-studies", 85),
    ("case-study", 85),
    ("customers", 85),
    ("testimonials", 85),
    ("reviews", 80),
    ("success-stories", 80),
    # About Us & Company
    ("about", 80),
    ("about-us", 80),
    ("company", 80),
    ("team", 75),
    ("our-story", 75),
    ("mission", 75),
    # FAQ & Support
    ("faq", 75),
    ("faqs", 75),
    ("help", 70),
    ("support", 70),
    # Contact & Locations
    ("contact", 70),
    ("contact-us", 70),
    ("locations", 65),
    ("reach-us", 65),
    # Documentation & Guides
    ("documentation", 65),
    ("docs", 65),
    ("guides", 65),
    ("api", 60),
    # Policies & Legal
    ("policies", 60),
    ("policy", 60),
    ("refund", 60),
    ("returns", 60),
    ("shipping", 60),
    ("delivery", 60),
    ("warranty", 60),
    ("terms", 55),
    ("privacy", 55),
    ("security", 55),
    # Content & Blog (Lower priority)
    ("blog", 30),
    ("posts", 30),
    ("news", 30),
    ("articles", 30),
]

PROACTIVE_HIGH_VALUE_PATHS = [
    "/about", "/about-us", "/pages/about", "/pages/about-us", "/pages/our-story", "/company",
    "/contact", "/contact-us", "/pages/contact", "/pages/contact-us", "/pages/reach-us",
    "/faq", "/faqs", "/pages/faq", "/pages/faqs", "/help",
    "/policies/refund-policy", "/pages/returns-exchange-policy", "/pages/refund-policy", "/pages/return-policy",
    "/policies/shipping-policy", "/pages/shipping-policy", "/pages/delivery-information",
    "/policies/terms-of-service", "/pages/terms-of-service", "/terms", "/privacy", "/policies/privacy-policy",
    "/collections", "/shop", "/pricing", "/plans", "/services"
]

class SitemapCrawler:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    @classmethod
    def prioritize_url(cls, url: str) -> int:
        path = urllib.parse.urlparse(url).path.lower().rstrip("/")
        if path == "" or path == "/":
            return 120  # Homepage is always top priority

        for keyword, score in PRIORITY_PATHS:
            if keyword in path:
                return score
        return 20  # Standard fallback priority

    @classmethod
    async def _parse_urlset_xml(cls, xml_bytes: bytes, base_url: str, discovered: set[str]):
        try:
            root = ET.fromstring(xml_bytes)
            for elem in root.iter():
                if elem.tag.endswith("loc") and elem.text:
                    norm = URLNormalizer.normalize(elem.text.strip())
                    if URLNormalizer.is_same_domain(base_url, norm):
                        discovered.add(norm)
        except Exception as e:
            logger.debug(f"Error parsing urlset XML: {e}")

    @classmethod
    async def discover_urls(cls, base_url: str, client: httpx.AsyncClient | None = None) -> list[tuple[str, int]]:
        """
        Discovers URLs from sitemap.xml, child sitemaps, and proactive high-value paths.
        Returns list of (normalized_url, priority_score).
        Section 4.1 Steps 19 & 20.
        """
        parsed = urllib.parse.urlparse(base_url)
        sitemap_candidates = [
            f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
            f"{parsed.scheme}://{parsed.netloc}/wp-sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap-products.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap-pages.xml",
        ]

        discovered: set[str] = set()
        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=cls.HEADERS)
            owns_client = True

        try:
            for s_url in sitemap_candidates:
                try:
                    resp = await client.get(s_url)
                    if resp.status_code == 200:
                        text_lower = resp.text.lower()
                        # Case 1: Sitemap Index (Parent sitemap pointing to child sitemaps)
                        if "<sitemapindex" in text_lower:
                            root = ET.fromstring(resp.content)
                            child_sitemaps: list[str] = []
                            for elem in root.iter():
                                if elem.tag.endswith("loc") and elem.text:
                                    c_url = elem.text.strip()
                                    if URLNormalizer.is_same_domain(base_url, c_url):
                                        child_sitemaps.append(c_url)

                            # Prioritize high-value child sitemaps (products, pages, collections, services)
                            def score_child(u: str) -> int:
                                u_low = u.lower()
                                if any(k in u_low for k in ["product", "page", "service", "collection", "pricing"]):
                                    return 100
                                if any(k in u_low for k in ["policy", "legal", "terms", "faq", "category"]):
                                    return 70
                                if any(k in u_low for k in ["post", "blog", "article"]):
                                    return 40
                                return 10

                            child_sitemaps.sort(key=score_child, reverse=True)

                            # Fetch up to 20 child sitemaps to ensure deep, complete coverage
                            for child_url in child_sitemaps[:20]:
                                try:
                                    c_resp = await client.get(child_url)
                                    if c_resp.status_code == 200:
                                        await cls._parse_urlset_xml(c_resp.content, base_url, discovered)
                                except Exception as ce:
                                    logger.debug(f"Failed parsing child sitemap {child_url}: {ce}")

                            if discovered:
                                break

                        # Case 2: Flat urlset
                        elif "<urlset" in text_lower:
                            await cls._parse_urlset_xml(resp.content, base_url, discovered)
                            if discovered:
                                break

                except Exception as e:
                    logger.debug(f"Failed parsing sitemap candidate {s_url}: {e}")
        finally:
            if owns_client:
                await client.aclose()

        # Proactively seed standard high-value endpoints (Rule 19 & 20)
        for path in PROACTIVE_HIGH_VALUE_PATHS:
            cand = urllib.parse.urljoin(base_url, path)
            norm = URLNormalizer.normalize(cand)
            if URLNormalizer.is_same_domain(base_url, norm):
                discovered.add(norm)

        # Always include base url / home page
        discovered.add(URLNormalizer.normalize(base_url))

        # Sort by priority score
        scored = [(url, cls.prioritize_url(url)) for url in discovered]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    @classmethod
    def stratify_urls(cls, scored_urls: list[tuple[str, int]], max_budget: int = 75) -> list[str]:
        """
        Section 4.1 Rule 20: Stratified categorical crawl budgeting.
        Partitions all discovered URLs into guaranteed functional buckets so that high-value
        Policies, FAQs, Contact, About, and Collections are NEVER crowded out by thousands of product variants.
        """
        buckets: dict[str, list[tuple[str, int]]] = {
            "HOME": [],
            "POLICIES": [],
            "ABOUT": [],
            "CONTACT": [],
            "FAQS": [],
            "PRICING": [],
            "COLLECTIONS": [],
            "PROOF": [],
            "DOCUMENTATION": [],
            "PRODUCTS": [],
            "OTHER": []
        }

        for url, score in scored_urls:
            path = urllib.parse.urlparse(url).path.lower().rstrip("/")
            if path == "" or path == "/":
                buckets["HOME"].append((url, score))
            elif any(k in path for k in ["refund", "return", "exchange", "shipping", "delivery", "policy", "policies", "terms", "privacy", "warranty", "security"]):
                buckets["POLICIES"].append((url, score))
            elif any(k in path for k in ["about", "our-story", "story", "company", "mission", "team", "who-we-are"]):
                buckets["ABOUT"].append((url, score))
            elif any(k in path for k in ["contact", "reach-us", "locations", "support", "help-center"]):
                buckets["CONTACT"].append((url, score))
            elif any(k in path for k in ["faq", "faqs", "help", "frequently-asked-questions"]):
                buckets["FAQS"].append((url, score))
            elif any(k in path for k in ["pricing", "plans", "cost", "fees", "subscription", "rates"]):
                buckets["PRICING"].append((url, score))
            elif any(k in path for k in ["collection", "collections", "category", "categories", "services", "service", "solutions", "solution", "industry", "industries"]):
                buckets["COLLECTIONS"].append((url, score))
            elif any(k in path for k in ["case-study", "case-studies", "testimonials", "reviews", "customers", "success-stories"]):
                buckets["PROOF"].append((url, score))
            elif any(k in path for k in ["docs", "documentation", "guides", "api", "manual"]):
                buckets["DOCUMENTATION"].append((url, score))
            elif any(k in path for k in ["product", "products", "item", "items", "shop", "store"]):
                buckets["PRODUCTS"].append((url, score))
            else:
                buckets["OTHER"].append((url, score))

        # Sort each bucket by priority score descending
        for b_name in buckets:
            buckets[b_name].sort(key=lambda x: x[1], reverse=True)

        selected: list[str] = []
        selected_set: set[str] = set()

        def add_url(u: str):
            if u not in selected_set and len(selected) < max_budget:
                selected_set.add(u)
                selected.append(u)

        # 1. Tier 1: 100% Guaranteed Quotas
        # Home
        for u, _ in buckets["HOME"]:
            add_url(u)
        # Commercial Policies (Up to 8)
        for u, _ in buckets["POLICIES"][:8]:
            add_url(u)
        # About Us & Company (Up to 4)
        for u, _ in buckets["ABOUT"][:4]:
            add_url(u)
        # Contact Us & Support (Up to 4)
        for u, _ in buckets["CONTACT"][:4]:
            add_url(u)
        # FAQs & Help (Up to 6)
        for u, _ in buckets["FAQS"][:6]:
            add_url(u)
        # Pricing & Commercial Plans (Up to 6)
        for u, _ in buckets["PRICING"][:6]:
            add_url(u)

        # 2. Tier 2: Category & Proof Index Pages
        # Collections & Category taxonomy (Up to 12)
        for u, _ in buckets["COLLECTIONS"][:12]:
            add_url(u)
        # Case Studies & Testimonials (Up to 5)
        for u, _ in buckets["PROOF"][:5]:
            add_url(u)
        # Documentation & Guides (Up to 5)
        for u, _ in buckets["DOCUMENTATION"][:5]:
            add_url(u)

        # 3. Tier 3: Representative Catalog Offerings (Up to 35 diverse items)
        for u, _ in buckets["PRODUCTS"][:35]:
            add_url(u)

        # 4. Fill remaining budget with any remaining high-priority items across all buckets
        remaining_pool: list[tuple[str, int]] = []
        for b_name, items in buckets.items():
            for u, s in items:
                if u not in selected_set:
                    remaining_pool.append((u, s))

        remaining_pool.sort(key=lambda x: x[1], reverse=True)
        for u, _ in remaining_pool:
            if len(selected) >= max_budget:
                break
            add_url(u)

        return selected

