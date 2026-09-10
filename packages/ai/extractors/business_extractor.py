import re
import urllib.parse
from datetime import datetime, timezone
from typing import Sequence
from packages.website_intelligence.fetcher import FetchedPage

class BusinessExtractor:
    """
    Section 4.1 Rule 26 & 28: Extracts structured company facts from crawled website pages
    with strict source provenance (statement, source_url, confidence, fact_type, extracted_at).
    Section 4.1 Rule 29: Evaluates quality and surfaces low-confidence fields for human review.
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
        policies = []
        contact_info = {"emails": [], "phones": [], "whatsapp": [], "addresses": []}
        structured_facts = []

        now_iso = datetime.now(timezone.utc).isoformat()
        generic_titles = {
            "home", "pricing", "product", "products", "features", "solutions",
            "about", "about us", "contact", "contact us", "terms", "refund policy",
            "privacy", "blog", "collections", "shop", "catalog", "cart", "checkout"
        }
        ui_modal_titles = {
            "item added to your cart", "added to your cart", "shopping cart", "your cart", "cart",
            "quick view", "skip to content", "customer reviews", "related products", "you may also like",
            "recently viewed", "filter by", "sort by", "leave a comment", "subscribe to our newsletter",
            "share this product", "close", "menu", "search our store", "my account", "sign in", "create account",
            "order summary", "subtotal", "total", "checkout", "view cart", "continue shopping"
        }
        extracted_description = ""

        # Step 1: Detect Company Name & Legal Identity
        if not company_name:
            # Pass 1: Homepage title
            for p in pages:
                parsed_path = urllib.parse.urlparse(p.url).path.rstrip("/").lower()
                if parsed_path == "" and p.cleaned.title:
                    parts = re.split(r"\s*\|\s*|\s+[-–—•]\s+", p.cleaned.title)
                    candidate = parts[0].strip()
                    if candidate.lower() not in generic_titles and len(candidate) > 1:
                        company_name = candidate
                        break

            # Pass 2: Any page title separator
            if not company_name:
                for p in pages:
                    if p.cleaned.title:
                        parts = re.split(r"\s*\|\s*|\s+[-–—•]\s+", p.cleaned.title)
                        candidate = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
                        if candidate.lower() not in generic_titles and len(candidate) > 1:
                            company_name = candidate
                            break

            # Pass 3: Netloc fallback
            if not company_name and pages:
                netloc = urllib.parse.urlparse(pages[0].url).netloc
                company_name = netloc.replace("www.", "").split(".")[0].capitalize()

        # Step 2: Iterate across all crawled pages and extract details
        for p in pages:
            url = p.url
            text = p.cleaned.text
            title = p.cleaned.title
            page_type = getattr(p.cleaned, "page_type", "OTHER")

            # Capture meta description
            if not extracted_description and getattr(p.cleaned, "meta_description", ""):
                extracted_description = p.cleaned.meta_description

            # 1. Contact Signals (Emails, Phones, WhatsApp, Addresses)
            if hasattr(p.cleaned, "contact_signals"):
                for em in p.cleaned.contact_signals.get("emails", []):
                    if em not in contact_info["emails"]:
                        contact_info["emails"].append(em)
                        structured_facts.append({
                            "statement": f"Official contact email: {em}",
                            "source_url": url,
                            "fact_type": "CONTACT",
                            "confidence": 0.98,
                            "extracted_at": now_iso
                        })
                for ph in p.cleaned.contact_signals.get("phones", []):
                    if ph not in contact_info["phones"]:
                        contact_info["phones"].append(ph)
                        structured_facts.append({
                            "statement": f"Official phone / support number: {ph}",
                            "source_url": url,
                            "fact_type": "CONTACT",
                            "confidence": 0.95,
                            "extracted_at": now_iso
                        })
                for wa in p.cleaned.contact_signals.get("whatsapp", []):
                    if wa not in contact_info["whatsapp"]:
                        contact_info["whatsapp"].append(wa)
                        structured_facts.append({
                            "statement": f"Direct WhatsApp support: {wa}",
                            "source_url": url,
                            "fact_type": "CONTACT",
                            "confidence": 0.98,
                            "extracted_at": now_iso
                        })

            # 2. Approved Call-to-Actions (CTAs)
            cta_matches = re.findall(
                r"\b(shop now|buy now|add to cart|order now|contact us|get a quote|schedule demo|explore collection)\b",
                text,
                re.I
            )
            for c in cta_matches:
                cta_item = {"action": c.capitalize(), "source_url": url}
                if cta_item not in ctas:
                    ctas.append(cta_item)

            # 3. Product & Catalog Extraction (up to 30 items)
            is_catalog_or_product = page_type in ("PRODUCT_CATALOG", "PRODUCT_DETAIL") or any(
                k in url.lower() for k in ["product", "service", "collection", "category", "shop", "catalog"]
            )
            if is_catalog_or_product:
                # Extract item from title using proper delimiter splitting
                title_parts = re.split(r"\s*\|\s*|\s+[-–—•]\s+", title) if title else []
                clean_title = title_parts[0].strip() if title_parts else ""

                if (
                    len(clean_title) > 3
                    and clean_title.lower() not in generic_titles
                    and clean_title.lower() not in ui_modal_titles
                ):
                    # Detect price for this specific item if present on page
                    item_price_match = re.search(r"(?:Rs\.?|PKR|£|€|₹|\$)\s*\d[\d,]*(?:\.\d{2})?", text, re.I)
                    item_price = item_price_match.group(0).strip() if item_price_match else None

                    offering_item = {
                        "title": clean_title,
                        "category": "Products & Apparel" if any(k in url.lower() for k in ["lawn", "suit", "dress", "clothing", "collection"]) else "Core Services",
                        "price": item_price,
                        "source_url": url
                    }
                    if not any(o["title"].lower() == clean_title.lower() for o in offerings):
                        offerings.append(offering_item)
                        structured_facts.append({
                            "statement": f"Offering '{clean_title}'" + (f" priced at {item_price}" if item_price else ""),
                            "source_url": url,
                            "fact_type": "OFFERING",
                            "confidence": 0.95,
                            "extracted_at": now_iso
                        })

                # Also extract H2 headings as sub-products or collections (filtering out UI modals)
                for line in text.splitlines():
                    line_s = line.strip()
                    if line_s.startswith("## ") and 4 < len(line_s) < 80:
                        h2_title = line_s[3:].strip()
                        if (
                            h2_title.lower() not in generic_titles
                            and h2_title.lower() not in ui_modal_titles
                            and not any(o["title"].lower() == h2_title.lower() for o in offerings)
                        ):
                            offerings.append({
                                "title": h2_title,
                                "category": "Collection / Feature",
                                "source_url": url
                            })

            # 4. Features & Specs
            for line in text.splitlines():
                line_s = line.strip()
                if line_s.startswith("- ") and 10 < len(line_s) < 140:
                    feat_text = line_s[2:].strip()
                    feat_item = {"name": feat_text, "source_url": url}
                    if not any(f["name"].lower() == feat_text.lower() for f in features):
                        features.append(feat_item)

            # 5. Pricing & Commercials
            price_matches = re.findall(r"(?:Rs\.?|PKR|£|€|₹|\$)\s*\d[\d,]*(?:\.\d{2})?", text, re.I)
            if price_matches and not pricing_data:
                currency_detected = "USD"
                if any("pkr" in m.lower() or "rs" in m.lower() for m in price_matches):
                    currency_detected = "PKR"
                elif any("£" in m for m in price_matches):
                    currency_detected = "GBP"
                elif any("€" in m for m in price_matches):
                    currency_detected = "EUR"
                elif any("₹" in m for m in price_matches):
                    currency_detected = "INR"

                # Check free shipping threshold
                free_shipping = re.search(r"free\s+(?:shipping|delivery)\s+(?:on|above|over)?\s*(?:orders\s+)?((?:Rs\.?|PKR|£|€|₹|\$)\s*[\d,]+)", text, re.I)
                free_ship_str = free_shipping.group(0).strip() if free_shipping else None

                pricing_data = {
                    "model": "PUBLIC_TIERS",
                    "currency": currency_detected,
                    "detected_signals": [p.strip() for p in price_matches[:10]],
                    "free_shipping_offer": free_ship_str,
                    "source_url": url,
                    "requires_human_review": False
                }
                structured_facts.append({
                    "statement": f"Pricing detected with currency {currency_detected}: Sample rates {', '.join(price_matches[:3])}",
                    "source_url": url,
                    "fact_type": "PRICING",
                    "confidence": 0.95,
                    "extracted_at": now_iso
                })

            # 6. Value Propositions & Benefits
            if any(k in text.lower() for k in ["why choose", "benefits", "guarantee", "delivery all over", "nationwide", "fast shipping", "premium quality"]):
                for line in text.splitlines():
                    line_clean = line.strip("- #*").strip()
                    if any(w in line_clean.lower() for w in [
                        "delivery all over", "nationwide", "free shipping", "guarantee",
                        "premium", "reduce", "increase", "automate", "100% genuine", "original"
                    ]) and 15 < len(line_clean) < 140:
                        prop_item = {"benefit": line_clean, "source_url": url}
                        if not any(v["benefit"].lower() == line_clean.lower() for v in value_props):
                            value_props.append(prop_item)
                            structured_facts.append({
                                "statement": f"Value proposition: {line_clean}",
                                "source_url": url,
                                "fact_type": "VALUE_PROP",
                                "confidence": 0.90,
                                "extracted_at": now_iso
                            })

            # 7. FAQs (From structured accordions and Q&A blocks)
            if hasattr(p.cleaned, "faq_candidates"):
                for cand in p.cleaned.faq_candidates:
                    q = cand["question"]
                    a = cand["answer"]
                    if not any(f["question"].lower() == q.lower() for f in faqs):
                        faq_obj = {"question": q, "answer": a, "source_url": url}
                        faqs.append(faq_obj)
                        structured_facts.append({
                            "statement": f"FAQ: Q: {q} | A: {a[:150]}...",
                            "source_url": url,
                            "fact_type": "FAQ",
                            "confidence": 0.95,
                            "extracted_at": now_iso
                        })

            faq_blocks = re.findall(r"(?:Q:|###\s*)(.*?)\n+(?:A:)?(.*?)(?=\n###|\nQ:|\Z)", text, re.S)
            for q, a in faq_blocks:
                q_clean = q.strip()
                a_clean = a.strip()
                if "?" in q_clean and len(a_clean) > 20:
                    if not any(f["question"].lower() == q_clean.lower() for f in faqs):
                        faqs.append({"question": q_clean, "answer": a_clean[:400], "source_url": url})

            # 8. Policies (Return, Refund, Shipping, Exchange)
            policy_matches = re.findall(r"(?:(?:return|refund|exchange|shipping|delivery)\s+policy|(\d+)\s*days?\s+(?:return|exchange|money back))", text, re.I)
            if policy_matches or page_type == "LEGAL_POLICY":
                for line in text.splitlines():
                    line_s = line.strip("- #*").strip()
                    if any(w in line_s.lower() for w in ["return", "exchange", "refund", "shipping", "delivery time", "transit"]) and 20 < len(line_s) < 160:
                        pol_item = {"policy": line_s, "source_url": url}
                        if not any(pl["policy"].lower() == line_s.lower() for pl in policies):
                            policies.append(pol_item)
                            structured_facts.append({
                                "statement": f"Policy rule: {line_s}",
                                "source_url": url,
                                "fact_type": "POLICY",
                                "confidence": 0.95,
                                "extracted_at": now_iso
                            })

            # 9. Proof & Metrics & Reviews
            proof_matches = re.findall(r"(\d+%\s+(?:increase|decrease|growth|improvement|reduction|satisfaction|money back)[^.\n]*)", text, re.I)
            for m in proof_matches:
                proof_points.append({"metric": m.strip(), "source_url": url})

            # 10. Industries
            for ind in [
                "SaaS & Cloud", "Healthcare & Life Sciences", "Fintech & Banking", "E-commerce & Retail",
                "Fashion & Apparel", "Manufacturing & Logistics", "Agencies & Consulting", "Real Estate",
                "Education & EdTech", "Consumer Goods"
            ]:
                if re.search(rf"\b{re.escape(ind.split()[0])}\b", text, re.I):
                    industries.add(ind)

        # Fallback values
        if not company_name:
            company_name = "Target Enterprise"

        if not pricing_data:
            pricing_data = {
                "model": "CONTACT_SALES",
                "notes": "No public pricing detected on crawled pages",
                "requires_human_review": True
            }

        if not extracted_description or len(extracted_description.strip()) < 15:
            if offerings:
                sample_items = ", ".join([o["title"] for o in offerings[:4]])
                final_description = f"{company_name} is an active brand and business offering {sample_items}."
            else:
                final_description = f"Autonomous business intelligence and sales knowledge grounded for {company_name}."
        else:
            final_description = extracted_description

        # Section 4.1 Rule 29: Quality checks and surface low-confidence fields for human review
        confidence_calc = 0.60
        review_reasons = []

        if company_name and company_name != "Target Enterprise":
            confidence_calc += 0.10
        if len(offerings) >= 3:
            confidence_calc += 0.10
        if pricing_data.get("model") == "PUBLIC_TIERS":
            confidence_calc += 0.10
        else:
            review_reasons.append("Pricing tiers not publicly listed; requires human verification.")
        if len(value_props) >= 2 or len(policies) >= 1:
            confidence_calc += 0.05
        if len(faqs) >= 1 or len(contact_info["emails"]) >= 1 or len(contact_info["phones"]) >= 1:
            confidence_calc += 0.03

        confidence_score = round(min(confidence_calc, 0.98), 2)
        requires_human_review = confidence_score < 0.85 or pricing_data.get("requires_human_review", False)

        return {
            "company_name": company_name,
            "legal_name": None,
            "description": final_description[:600],
            "offerings": offerings[:30],
            "value_propositions": value_props[:12],
            "industries": list(industries) or ["E-commerce & Retail"],
            "icp_hints": {
                "target_customers": "Direct-to-consumer shoppers & wholesale purchasers" if "Fashion & Apparel" in industries else "B2B Decision Makers & Growth Leaders",
                "roles": ["Purchaser", "Head of Sales", "Founder", "Director of Growth", "Category Manager"],
                "company_size": "1-500 employees"
            },
            "pricing": pricing_data,
            "features": features[:20],
            "faqs": faqs[:15],
            "proof": proof_points[:8],
            "policies": policies[:10],
            "contact_info": contact_info,
            "structured_facts": structured_facts[:50],
            "brand_voice": {
                "tone": "Direct, consultative, customer-centric, reliable",
                "formality": "High"
            },
            "claims_policy": {
                "allowed_claims": [p["metric"] for p in proof_points[:3]] or [v["benefit"] for v in value_props[:3]],
                "forbidden_claims": ["Unverified discounts", "Unlimited refunds without product return", "Guaranteed 10x ROI without contract"],
                "policies": policies[:10],
                "contact_info": contact_info,
                "structured_facts": structured_facts[:50],
                "requires_human_review": requires_human_review,
                "review_reasons": review_reasons
            },
            "ctas": ctas[:6] or [{"action": "Explore products and offerings", "source_url": pages[0].url if pages else ""}],
            "confidence_score": confidence_score,
            "requires_human_review": requires_human_review,
            "review_reasons": review_reasons
        }
