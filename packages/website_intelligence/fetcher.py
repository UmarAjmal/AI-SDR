import logging
import httpx
from packages.website_intelligence.cleaner import ContentCleaner, CleanedContent

logger = logging.getLogger("codenter.crawler.fetcher")

class FetchedPage:
    def __init__(
        self,
        url: str,
        status_code: int,
        html: str,
        cleaned: CleanedContent,
        extraction_method: str = "HTTP",
        screenshot_url: str | None = None
    ):
        self.url = url
        self.status_code = status_code
        self.html = html
        self.cleaned = cleaned
        self.extraction_method = extraction_method
        self.screenshot_url = screenshot_url

class HybridPageFetcher:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
    }

    @classmethod
    def is_spa_shell(cls, html: str, text_length: int) -> bool:
        """
        Detects if static HTML is merely an empty single-page application shell (React/Next/Vue).
        """
        if text_length < 150:
            if any(marker in html for marker in ['id="root"', 'id="__next"', 'id="app"', '<noscript>You need to enable JavaScript']):
                return True
        return False

    @classmethod
    async def fetch(cls, url: str, client: httpx.AsyncClient | None = None) -> FetchedPage:
        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=cls.HEADERS)
            owns_client = True

        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
            cleaned = ContentCleaner.clean_html(html, base_url=url)
            method = "HTTP"

            # Check if JavaScript rendering is required
            if cls.is_spa_shell(html, len(cleaned.text)):
                logger.info(f"SPA shell detected for {url}. Attempting Playwright rendering...")
                try:
                    # Attempt dynamic Playwright rendering
                    from playwright.async_api import async_playwright
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        page = await browser.new_page()
                        await page.goto(url, wait_until="networkidle", timeout=20000)
                        rendered_html = await page.content()
                        await browser.close()
                        html = rendered_html
                        cleaned = ContentCleaner.clean_html(html, base_url=url)
                        method = "PLAYWRIGHT"
                except Exception as pe:
                    logger.warning(f"Playwright rendering failed or not installed ({pe}); proceeding with HTTP content.")

            return FetchedPage(
                url=str(resp.url),
                status_code=resp.status_code,
                html=html,
                cleaned=cleaned,
                extraction_method=method,
                screenshot_url=None
            )
        except Exception as e:
            logger.error(f"Failed fetching {url}: {e}")
            raise
        finally:
            if owns_client:
                await client.aclose()
