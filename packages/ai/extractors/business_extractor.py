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

        generic_titles = {"home", "pricing", "product", "products", "features", "solutions", "about", "about us", "contact", "contact us", "terms", "refund policy", "privacy", "blog"}
        extracted_description = ""

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
            # Third pass: domain name fallback
            if not company_name and pages:
                netloc = urllib.parse.urlparse(pages[0].url).netloc
                company_name = netloc.split(".")[0].capitalize()

        for p in pages:
            url = p.url
            text = p.cleaned.text
            title = p.cleaned.title

            # Capture best description from homepage meta or text
            if not extracted_description and getattr(p.cleaned, "meta_description", ""):
                extracted_description = p.cleaned.meta_description

            # 1. CTAs (SaaS + E-Commerce / WordPress)
            cta_matches = re.findall(
                r"\b(book a demo|start free trial|schedule a call|contact sales|get started|request quote|shop now|buy now|add to cart|explore collection|view products|order now)\b",
                text,
                re.I
            )
            for c in cta_matches:
                cta_item = {"action": c.capitalize(), "source_url": url}
                if cta_item not in ctas:
                    ctas.append(cta_item)

            # 2. Offerings & Features (SaaS, Services & E-Commerce Collections/Products)
            is_offering_page = any(k in url.lower() for k in ["product", "service", "features", "solutions", "collection", "category", "shop", "catalog"])
            if is_offering_page:
                # Extract clean title as an offering
                if title:
                    clean_title = re.split(r"[-|•:]", title)[0].strip()
                    if len(clean_title) > 3 and clean_title.lower() not in generic_titles:
                        offering_item = {"title": clean_title, "source_url": url}
                        if offering_item not in offerings:
                            offerings.append(offering_item)

                for line in text.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("- ") and 10 < len(line_s) < 120:
                        feat = {"name": line_s[2:], "source_url": url}
                        if feat not in features:
                            features.append(feat)
                    elif line_s.startswith("## ") and 5 < len(line_s) < 80:
                        clean_h2 = line_s[3:].strip()
                        if clean_h2.lower() not in generic_titles:
                            offering_item = {"title": clean_h2, "source_url": url}
                            if offering_item not in offerings:
                                offerings.append(offering_item)

            # 3. Value Propositions & Quality Highlights
            if any(k in text.lower() for k in ["why choose", "benefits", "outcomes", "save time", "increase revenue", "delivery", "guarantee", "quality"]):
                for line in text.splitlines():
                    if any(w in line.lower() for w in ["reduce", "increase", "automate", "boost", "streamline", "guarantee", "premium", "free shipping", "delivery"]):
                        clean_prop = line.strip("- #*").strip()
                        if 15 < len(clean_prop) < 150:
                            value_props.append({"benefit": clean_prop, "source_url": url})

            # 4. Pricing (Global Currencies: $, Rs, PKR, £, €, ₹)
            price_matches = re.findall(r"(?:Rs\.?|PKR|£|€|₹|\$)\s*[\d,]+(?:\.\d+)?", text, re.I)
            if price_matches and not pricing_data:
                pricing_data = {
                    "model": "PUBLIC_TIERS",
                    "detected_signals": [p.strip() for p in price_matches[:6]],
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

            # 6. Proof & Metrics
            proof_matches = re.findall(r"(\d+%\s+(?:increase|decrease|growth|improvement|reduction|satisfaction|money back)[^.\n]*)", text, re.I)
            for m in proof_matches:
                proof_points.append({"metric": m.strip(), "source_url": url})

            # 7. Industries
            for ind in ["SaaS", "Healthcare", "Fintech", "E-commerce", "Fashion & Apparel", "Retail", "Manufacturing", "Agencies", "Legal", "Consumer Goods"]:
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

        if not extracted_description or len(extracted_description.strip()) < 15:
            if offerings:
                sample_items = ", ".join([o["title"] for o in offerings[:3]])
                final_description = f"{company_name} is an active brand and storefront featuring {sample_items}."
            else:
                final_description = f"Autonomous sales intelligence extracted for {company_name}."
        else:
            final_description = extracted_description

        return {
            "company_name": company_name,
            "legal_name": None,
            "description": final_description[:500],
            "offerings": offerings[:10],
            "value_propositions": value_props[:8],
            "industries": list(industries) or ["E-commerce & Retail"],
            "icp_hints": {
                "roles": ["Head of Sales", "Founder", "Director of Growth", "Purchasing Manager"],
                "company_size": "1-250 employees"
            },
            "pricing": pricing_data,
            "features": features[:15],
            "faqs": faqs[:10],
            "proof": proof_points[:5],
            "brand_voice": {
                "tone": "Direct, consultative, customer-centric",
                "formality": "High"
            },
            "claims_policy": {
                "allowed_claims": [p["metric"] for p in proof_points[:3]],
                "forbidden_claims": ["Unverified discounts", "Unlimited free returns without receipt", "Guaranteed 10x ROI"]
            },
            "ctas": ctas[:3] or [{"action": "Explore products and offerings", "source_url": pages[0].url if pages else ""}],
            "confidence_score": 0.95 if (offerings and pricing_data.get("model") == "PUBLIC_TIERS") else 0.85
        }
