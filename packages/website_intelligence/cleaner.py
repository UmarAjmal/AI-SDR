import hashlib
import re
import urllib.parse
from bs4 import BeautifulSoup

class CleanedContent:
    def __init__(
        self,
        title: str,
        text: str,
        content_hash: str,
        internal_links: list[str],
        meta_description: str = "",
        headings: list[dict] | None = None,
        page_type: str = "OTHER",
        business_topic: str = "GENERAL",
        structured_tables: list[str] | None = None,
        contact_signals: dict | None = None,
        faq_candidates: list[dict] | None = None
    ):
        self.title = title
        self.text = text
        self.content_hash = content_hash
        self.internal_links = internal_links
        self.meta_description = meta_description
        self.headings = headings or []
        self.page_type = page_type
        self.business_topic = business_topic
        self.structured_tables = structured_tables or []
        self.contact_signals = contact_signals or {}
        self.faq_candidates = faq_candidates or []

class ContentCleaner:
    # Section 4.1 Rule 24: Remove navigation, footer, scripts, styles, boilerplate duplication
    BOILERPLATE_TAGS = {"script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form", "iframe"}

    @classmethod
    def _table_to_markdown(cls, table_elem) -> str:
        """Preserves HTML pricing, spec, and comparison tables as clean Markdown tables."""
        rows = table_elem.find_all("tr")
        if not rows:
            return ""
        table_data = []
        for r in rows:
            cells = [c.get_text().strip().replace("\n", " ") for c in r.find_all(["th", "td"])]
            if any(cells):
                table_data.append(cells)
        if not table_data:
            return ""
        max_cols = max(len(r) for r in table_data)
        padded = [r + [""] * (max_cols - len(r)) for r in table_data]
        lines = []
        lines.append("| " + " | ".join(padded[0]) + " |")
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        for r in padded[1:]:
            lines.append("| " + " | ".join(r) + " |")
        return "\n".join(lines)

    @classmethod
    def _classify_page(cls, url: str, title: str, headings: list[dict]) -> tuple[str, str]:
        """
        Section 4.1 Rule 25: Classify page type and business topic.
        """
        path = urllib.parse.urlparse(url).path.lower().rstrip("/")
        title_lower = title.lower()
        headings_text = " ".join([h.get("text", "").lower() for h in headings])
        combined = f"{path} {title_lower} {headings_text}"

        if path == "" or path == "/":
            return "HOME", "COMPANY_INFO"

        if any(k in combined for k in ["pricing", "plans", "subscription", "cost", "membership"]):
            return "PRICING", "PRICING_MODEL"

        if "/products/" in path or "/product/" in path or "/item/" in path:
            return "PRODUCT_DETAIL", "CORE_OFFERING"

        if any(k in combined for k in ["collection", "catalog", "shop", "products", "services", "store"]):
            return "PRODUCT_CATALOG", "CORE_OFFERING"

        if any(k in combined for k in ["contact", "locations", "reach-us", "get-in-touch"]):
            return "CONTACT", "COMPANY_INFO"

        if any(k in combined for k in ["faq", "faqs", "help", "support", "questions", "knowledgebase"]):
            return "FAQ", "SUPPORT_POLICY"

        if any(k in combined for k in ["case-stud", "customer", "testimonial", "reviews", "success-stor"]):
            return "CASE_STUDY", "CUSTOMER_PROOF"

        if any(k in combined for k in ["refund", "return", "shipping", "delivery", "terms", "privacy", "policy", "warranty", "legal"]):
            return "LEGAL_POLICY", "LEGAL_COMPLIANCE"

        if any(k in combined for k in ["doc", "guide", "manual", "api-reference", "developer"]):
            return "DOCUMENTATION", "TECHNICAL_DOC"

        if any(k in combined for k in ["about", "our-story", "leadership", "mission", "team", "company"]):
            return "ABOUT_US", "COMPANY_INFO"

        if any(k in combined for k in ["blog", "news", "articles", "posts"]):
            return "BLOG_POST", "GENERAL"

        return "OTHER", "GENERAL"

    @classmethod
    def clean_html(cls, html_content: str, base_url: str = "") -> CleanedContent:
        if not html_content:
            return CleanedContent(
                title="",
                text="",
                content_hash="",
                internal_links=[],
                meta_description="",
                headings=[],
                page_type="OTHER",
                business_topic="GENERAL"
            )

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Extract Title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""

        # 1b. Extract Meta Description & Keywords
        meta_description = ""
        meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or \
                        soup.find("meta", attrs={"property": re.compile(r"og:description", re.I)})
        if meta_desc_tag and getattr(meta_desc_tag, "attrs", None):
            meta_description = str(meta_desc_tag.attrs.get("content", "")).strip()

        # 2. Extract links before stripping navigation (Rule 19)
        all_links: list[str] = []
        base_host = urllib.parse.urlparse(base_url).netloc.lower().replace("www.", "") if base_url else ""

        for a in soup.find_all("a", href=True):
            if not getattr(a, "attrs", None):
                continue
            raw_href = str(a.attrs.get("href", "")).strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Handle scheme-relative links (//example.com)
            if raw_href.startswith("//"):
                raw_href = "https:" + raw_href
            # Handle domain-like links missing protocol (e.g. www.tiktok.com or mydomain.myshopify.com)
            elif re.match(r"^(?:www\.|[a-zA-Z0-9-]+\.(?:myshopify\.com|com|pk|org|net|io|co|ai|app|store|shop))", raw_href, re.I):
                raw_href = "https://" + raw_href

            if base_url:
                full_url = urllib.parse.urljoin(base_url, raw_href)
                parsed = urllib.parse.urlparse(full_url)
                if parsed.scheme in ("http", "https"):
                    all_links.append(full_url)
            else:
                all_links.append(raw_href)

        # Strictly isolate internal links belonging to the same root domain
        internal_links: list[str] = []
        for l in all_links:
            if base_host:
                parsed_l = urllib.parse.urlparse(l)
                link_host = parsed_l.netloc.lower().replace("www.", "")
                if link_host == base_host and l not in internal_links:
                    internal_links.append(l)
            else:
                if l not in internal_links:
                    internal_links.append(l)

        # 2b. Extract Contact Signals (Email, Phone, WhatsApp, Address)
        raw_page_text = soup.get_text()
        raw_emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw_page_text)
        clean_emails: list[str] = []
        for em in raw_emails:
            # Strip accidental camelcase or glued trailing words (e.g. gmail.comCall -> gmail.com)
            em_clean = re.sub(r"(\.(?:com|pk|org|net|io|co|ai|app|store|shop|edu|gov))([A-Z][a-z]+.*)$", r"\1", em)
            if em_clean not in clean_emails:
                clean_emails.append(em_clean)

        phones = list(set(re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", raw_page_text)))
        clean_phones = [p.strip() for p in phones if len(re.sub(r"\D", "", p)) >= 10][:5]
        whatsapp_links = [
            l for l in all_links if "wa.me" in l or "whatsapp.com" in l
        ]

        contact_signals = {
            "emails": clean_emails[:5],
            "phones": clean_phones[:5],
            "whatsapp": whatsapp_links[:3]
        }

        # 2c. Extract Structured Accordions & FAQs before stripping tags
        faq_candidates: list[dict] = []
        for details in soup.find_all("details"):
            summary = details.find("summary")
            if summary:
                q_text = summary.get_text().strip()
                # Remove summary from details to get answer
                summary.extract()
                a_text = details.get_text().strip()
                if q_text and a_text:
                    faq_candidates.append({"question": q_text, "answer": a_text[:500]})

        for faq_el in soup.find_all(class_=re.compile(r"faq|accordion|question", re.I)):
            q_elem = faq_el.find(class_=re.compile(r"question|title|header|toggle", re.I))
            a_elem = faq_el.find(class_=re.compile(r"answer|body|content|panel", re.I))
            if q_elem and a_elem:
                q_txt = q_elem.get_text().strip()
                a_txt = a_elem.get_text().strip()
                if 5 < len(q_txt) < 200 and len(a_txt) > 10:
                    faq_candidates.append({"question": q_txt, "answer": a_txt[:500]})

        # 3. Strip boilerplate tags (Rule 24)
        for tag in soup(cls.BOILERPLATE_TAGS):
            tag.decompose()

        # 4. Remove cookie banners, popups, and newsletter overlays safely
        for div in soup.find_all(["div", "section", "aside"]):
            if not getattr(div, "attrs", None):
                continue
            cls_val = div.attrs.get("class", [])
            cls_str = " ".join(str(c) for c in cls_val) if isinstance(cls_val, list) else str(cls_val or "")
            id_str = str(div.attrs.get("id", "") or "")
            classes_and_ids = f"{cls_str} {id_str}".lower()
            if any(k in classes_and_ids for k in [
                "cookie", "consent", "banner", "newsletter-popup", "modal", "announcement-bar", "sticky-cart"
            ]):
                div.decompose()

        # 5. Extract Structured Headings Hierarchy (Rule 22)
        headings: list[dict] = []
        for h in soup.find_all(["h1", "h2", "h3", "h4"]):
            h_text = h.get_text().strip()
            if h_text:
                lvl = int(h.name[1])
                headings.append({"level": lvl, "text": h_text})

        # 6. Extract Tables into Clean Markdown (Tables are converted before general text extraction)
        structured_tables: list[str] = []
        for tbl in soup.find_all("table"):
            md_tbl = cls._table_to_markdown(tbl)
            if md_tbl:
                structured_tables.append(md_tbl)
                # Replace table with a p tag containing markdown table so it appears in cleaned text
                p_tag = soup.new_tag("p")
                p_tag.string = f"\n\n{md_tbl}\n\n"
                tbl.replace_with(p_tag)

        # 7. Extract structural text with Markdown formatting
        lines = []
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
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
            elif elem.name == "blockquote":
                lines.append(f"> {text}")
            else:
                lines.append(text)

        cleaned_text = "\n".join(lines)
        # Normalize excessive whitespace
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()

        # Compute SHA256 content hash
        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

        # 8. Classify Page Type and Topic (Rule 25)
        page_type, business_topic = cls._classify_page(base_url, title, headings)

        return CleanedContent(
            title=title,
            text=cleaned_text,
            content_hash=content_hash,
            internal_links=internal_links,
            meta_description=meta_description,
            headings=headings,
            page_type=page_type,
            business_topic=business_topic,
            structured_tables=structured_tables,
            contact_signals=contact_signals,
            faq_candidates=faq_candidates
        )

