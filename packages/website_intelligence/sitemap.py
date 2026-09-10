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

class SitemapCrawler:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    @classmethod
    def prioritize_url(cls, url: str) -> int:
        path = urllib.parse.urlparse(url).path.lower().rstrip("/")
        if path == "":
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
        Discovers URLs from sitemap.xml and child sitemaps, returning list of (normalized_url, priority_score).
        Handles flat <urlset> and hierarchical <sitemapindex> (Shopify, WordPress, Magento, Webflow).
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

        # Always include base url / home page
        discovered.add(URLNormalizer.normalize(base_url))

        # Sort by priority score
        scored = [(url, cls.prioritize_url(url)) for url in discovered]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

