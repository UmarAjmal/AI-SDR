import urllib.robotparser
import urllib.parse
import httpx
import logging

logger = logging.getLogger("codenter.crawler.robots")

class RobotsParser:
    def __init__(self, user_agent: str = "CodenterAI-SDR-Bot/1.0"):
        self.user_agent = user_agent
        self.parser = urllib.robotparser.RobotFileParser()
        self.crawl_delay = 0.5

    async def fetch_and_parse(self, base_url: str, client: httpx.AsyncClient | None = None) -> bool:
        """
        Fetches robots.txt for the given base_url.
        """
        parsed = urllib.parse.urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        owns_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
            owns_client = True

        try:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                self.parser.parse(resp.text.splitlines())
                delay = self.parser.crawl_delay(self.user_agent)
                if delay:
                    self.crawl_delay = max(delay, 0.5)
                return True
            else:
                # If 404, standard convention is crawling is permitted
                self.parser.allow_all = True
                return True
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt from {robots_url}: {e}")
            self.parser.allow_all = True
            return False
        finally:
            if owns_client:
                await client.aclose()

    def can_fetch(self, url: str) -> bool:
        return self.parser.can_fetch(self.user_agent, url)
