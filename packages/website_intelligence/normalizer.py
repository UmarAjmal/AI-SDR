import urllib.parse
import re

class URLNormalizer:
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "ref", "source"
    }

    @classmethod
    def normalize(cls, url: str) -> str:
        """
        Normalizes protocol, lowercases domain, strips fragments and tracking query parameters.
        """
        if not url:
            return ""

        url = url.strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = "https://" + url

        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Strip standard default ports
        if ":80" in netloc and scheme == "http":
            netloc = netloc.replace(":80", "")
        elif ":443" in netloc and scheme == "https":
            netloc = netloc.replace(":443", "")

        # Filter query params
        query_dict = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        filtered_query = [
            (k, v) for k, vs in query_dict.items() if k.lower() not in cls.TRACKING_PARAMS for v in vs
        ]
        sorted_query = urllib.parse.urlencode(sorted(filtered_query))

        path = parsed.path
        if not path:
            path = "/"
        elif len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        return urllib.parse.urlunparse((scheme, netloc, path, "", sorted_query, ""))

    @classmethod
    def extract_domain(cls, url: str) -> str:
        parsed = urllib.parse.urlparse(cls.normalize(url))
        return parsed.netloc

    @classmethod
    def is_same_domain(cls, url1: str, url2: str) -> bool:
        d1 = cls.extract_domain(url1).replace("www.", "")
        d2 = cls.extract_domain(url2).replace("www.", "")
        return d1 == d2
