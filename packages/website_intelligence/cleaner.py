import hashlib
import re
from bs4 import BeautifulSoup

class CleanedContent:
    def __init__(self, title: str, text: str, content_hash: str, internal_links: list[str]):
        self.title = title
        self.text = text
        self.content_hash = content_hash
        self.internal_links = internal_links

class ContentCleaner:
    BOILERPLATE_TAGS = {"script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"}

    @classmethod
    def clean_html(cls, html_content: str, base_url: str = "") -> CleanedContent:
        if not html_content:
            return CleanedContent(title="", text="", content_hash="", internal_links=[])

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""

        # 2. Extract internal links before stripping nav
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                links.append(href)

        # 3. Strip boilerplate tags
        for tag in soup(cls.BOILERPLATE_TAGS):
            tag.decompose()

        # 4. Remove cookie consent and banner divs
        for div in soup.find_all(["div", "section"]):
            classes_and_ids = " ".join([
                " ".join(div.get("class", [])),
                div.get("id", "")
            ]).lower()
            if any(k in classes_and_ids for k in ["cookie", "consent", "banner", "newsletter-popup"]):
                div.decompose()

        # 5. Extract structural text
        lines = []
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
            text = elem.get_text().strip()
            if not text:
                continue

            if elem.name == "h1":
                lines.append(f"\n# {text}\n")
            elif elem.name == "h2":
                lines.append(f"\n## {text}\n")
            elif elem.name == "h3":
                lines.append(f"\n### {text}\n")
            elif elem.name == "li":
                lines.append(f"- {text}")
            else:
                lines.append(text)

        cleaned_text = "\n".join(lines)
        # Normalize whitespace
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()

        # Compute SHA256
        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

        return CleanedContent(
            title=title,
            text=cleaned_text,
            content_hash=content_hash,
            internal_links=links
        )
