import urllib.parse
import xml.etree.ElementTree as ET
import httpx
import logging
from packages.website_intelligence.normalizer import URLNormalizer

logger = logging.getLogger("codenter.crawler.sitemap")

PRIORITY_PATHS = [
    ("pricing", 100),
    ("product", 90),
    ("services", 90),
    ("solutions", 85),
    ("features", 80),
    ("case-studies", 75),
    ("customers", 70),
    ("about", 65),
    ("faq", 60),
    ("contact", 50),
    ("security", 45),
    ("terms", 30),
    ("privacy", 30),
]

class SitemapCrawler:
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
    async def discover_urls(cls, base_url: str, client: httpx.AsyncClient | None = None) -> list[tuple[str, int]]:
        """
        Discovers URLs from sitemap.xml and returns list of (normalized_url, priority_score).
        """
        parsed = urllib.parse.urlparse(base_url)
        sitemap_urls = [
            f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        ]

        discovered: set[str] = set()
        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
            owns_client = True

        try:
            for s_url in sitemap_urls:
                try:
                    resp = await client.get(s_url)
                    if resp.status_code == 200 and "<urlset" in resp.text:
                        root = ET.fromstring(resp.content)
                        # Handle XML namespaces
                        for elem in root.iter():
                            if elem.tag.endswith("loc") and elem.text:
                                norm = URLNormalizer.normalize(elem.text.strip())
                                if URLNormalizer.is_same_domain(base_url, norm):
                                    discovered.add(norm)
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
