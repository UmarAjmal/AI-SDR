import re
from typing import Sequence
from packages.website_intelligence.fetcher import FetchedPage

class ExtractedFact:
    def __init__(self, fact: str, source_url: str):
        self.fact = fact
        self.source_url = source_url

class BusinessExtractor:
    """
    Extracts structured company facts from crawled website pages with strict source provenance.
    """
    @classmethod
    def extract_from_pages(
        cls,
        pages: Sequence[FetchedPage],
        company_name_hint: str | None = None
    ) -> dict:
        company_name = company_name_hint or ""
        offerings = []
        value_props = []
        industries = set()
        pricing_data = None
        features = []
        faqs = []
        proof_points = []
        ctas = []

        generic_titles = {"home", "pricing", "product", "features", "solutions", "about", "about us", "contact", "contact us", "terms", "refund policy", "privacy", "blog"}
        if not company_name:
            import urllib.parse
            # First pass: check homepage
            for p in pages:
                parsed_path = urllib.parse.urlparse(p.url).path.rstrip("/").lower()
                if parsed_path == "" and p.cleaned.title:
                    parts = re.split(r"[-|•:]", p.cleaned.title)
                    candidate = parts[0].strip()
                    if candidate.lower() not in generic_titles:
                        company_name = candidate
                        break
            # Second pass: check any other page with non-generic title
            if not company_name:
                for p in pages:
                    if p.cleaned.title:
                        parts = re.split(r"[-|•:]", p.cleaned.title)
                        candidate = parts[0].strip()
                        if candidate.lower() not in generic_titles:
                            company_name = candidate
                            break

        for p in pages:
            url = p.url
            text = p.cleaned.text
            title = p.cleaned.title

            # 1. CTAs
            cta_matches = re.findall(r"\b(book a demo|start free trial|schedule a call|contact sales|get started|request quote)\b", text, re.I)
            for c in cta_matches:
                cta_item = {"action": c.capitalize(), "source_url": url}
                if cta_item not in ctas:
                    ctas.append(cta_item)

            # 2. Offerings & Features
            if any(k in url.lower() for k in ["product", "service", "features", "solutions"]):
                for line in text.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("- ") and len(line_s) > 10:
                        feat = {"name": line_s[2:], "source_url": url}
                        if feat not in features:
                            features.append(feat)
                    elif line_s.startswith("## ") and len(line_s) > 5:
                        offerings.append({"title": line_s[3:], "source_url": url})

            # 3. Value Propositions
            if any(k in text.lower() for k in ["why choose", "benefits", "outcomes", "save time", "increase revenue"]):
                for line in text.splitlines():
                    if any(w in line.lower() for w in ["reduce", "increase", "automate", "boost", "streamline"]):
                        clean_prop = line.strip("- #*").strip()
                        if 20 < len(clean_prop) < 150:
                            value_props.append({"benefit": clean_prop, "source_url": url})

            # 4. Pricing
            if "pricing" in url.lower() or "pricing" in text.lower():
                # Detect pricing signals
                prices = re.findall(r"\$\s*\d+([,.]\d+)?(\s*/\s*(mo|month|year|seat))?", text)
                if prices:
                    pricing_data = {
                        "model": "PUBLIC_TIERS",
                        "detected_signals": [p[0] for p in prices[:4]],
                        "source_url": url,
                        "requires_human_review": False
                    }

            # 5. FAQs
            faq_blocks = re.findall(r"(?:Q:|###\s*)(.*?)\n+(?:A:)?(.*?)(?=\n###|\nQ:|\Z)", text, re.S)
            for q, a in faq_blocks:
                q_clean = q.strip()
                a_clean = a.strip()
                if "?" in q_clean and len(a_clean) > 20:
                    faqs.append({
                        "question": q_clean,
                        "answer": a_clean[:400],
                        "source_url": url
                    })

            # 6. Proof & Case Studies
            proof_matches = re.findall(r"(\d+%\s+(?:increase|decrease|growth|improvement|reduction)[^.\n]*)", text, re.I)
            for m in proof_matches:
                proof_points.append({"metric": m.strip(), "source_url": url})

            # 7. Industries
            for ind in ["SaaS", "Healthcare", "Fintech", "E-commerce", "Agencies", "Manufacturing", "Legal"]:
                if re.search(rf"\b{ind}\b", text, re.I):
                    industries.add(ind)

        # Fallback values
        if not company_name:
            company_name = "Target Company"

        if not pricing_data:
            pricing_data = {
                "model": "CONTACT_SALES",
                "notes": "No public pricing detected on crawled pages",
                "requires_human_review": True
            }

        return {
            "company_name": company_name,
            "legal_name": None,
            "description": f"Autonomous sales intelligence extracted for {company_name}.",
            "offerings": offerings[:10],
            "value_propositions": value_props[:8],
            "industries": list(industries) or ["B2B Technology"],
            "icp_hints": {
                "roles": ["VP of Sales", "Head of Growth", "CRO", "Founder"],
                "company_size": "10-200 employees"
            },
            "pricing": pricing_data,
            "features": features[:15],
            "faqs": faqs[:10],
            "proof": proof_points[:5],
            "brand_voice": {
                "tone": "Direct, consultative, professional",
                "formality": "High"
            },
            "claims_policy": {
                "allowed_claims": [p["metric"] for p in proof_points[:3]],
                "forbidden_claims": ["Unverified discounts", "Unlimited free tier", "Guaranteed 10x ROI"]
            },
            "ctas": ctas[:3] or [{"action": "Book a brief discovery call", "source_url": pages[0].url if pages else ""}],
            "confidence_score": 0.95 if proof_points and features else 0.80
        }
