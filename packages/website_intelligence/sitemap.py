import urllib.parse
import xml.etree.ElementTree as ET
import httpx
import logging
from packages.website_intelligence.normalizer import URLNormalizer

logger = logging.getLogger("codenter.crawler.sitemap")

PRIORITY_PATHS = [
    ("pricing", 100),
    ("products", 95),
    ("product", 95),
    ("collections", 90),
    ("collection", 90),
    ("services", 90),
    ("service", 90),
    ("solutions", 85),
    ("features", 80),
    ("case-studies", 75),
    ("customers", 70),
    ("about", 65),
    ("about-us", 65),
    ("faq", 60),
    ("faqs", 60),
    ("contact", 50),
    ("contact-us", 50),
    ("security", 45),
    ("policies", 35),
    ("policy", 35),
    ("terms", 30),
    ("privacy", 30),
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
            return 110  # Homepage is primary priority

        for keyword, score in PRIORITY_PATHS:
            if keyword in path:
                return score
        return 10  # Standard fallback priority

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
        Handles both flat <urlset> and hierarchical <sitemapindex> (Shopify, WordPress, Magento).
        """
        parsed = urllib.parse.urlparse(base_url)
        sitemap_urls = [
            f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
            f"{parsed.scheme}://{parsed.netloc}/wp-sitemap.xml",
        ]

        discovered: set[str] = set()
        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=cls.HEADERS)
            owns_client = True

        try:
            for s_url in sitemap_urls:
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

                            # Prioritize high-value child sitemaps (products, pages, services)
                            def score_child(u: str) -> int:
                                u_low = u.lower()
                                if any(k in u_low for k in ["product", "page", "service", "collection"]):
                                    return 100
                                if any(k in u_low for k in ["post", "category", "blog"]):
                                    return 50
                                return 10

                            child_sitemaps.sort(key=score_child, reverse=True)

                            # Fetch top 5 child sitemaps
                            for child_url in child_sitemaps[:5]:
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
                    logger.debug(f"Failed parsing sitemap {s_url}: {e}")
        finally:
            if owns_client:
                await client.aclose()

        # Always include base url / home page
        discovered.add(URLNormalizer.normalize(base_url))

        # Sort by priority
        scored = [(url, cls.prioritize_url(url)) for url in discovered]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

