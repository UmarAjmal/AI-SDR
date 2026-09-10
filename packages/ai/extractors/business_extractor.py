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
        legal_name = None
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
            "privacy", "privacy policy", "return policy", "shipping policy", "terms of service",
            "terms & conditions", "terms and conditions", "frequently asked questions",
            "blog", "collections", "shop", "catalog", "cart", "checkout",
            "faqs", "faq", "returns", "exchange policy", "refund and exchange policy",
            "store locator", "loyalty points", "rewards", "shipping & returns", "shipping and returns",
            "size guide", "size chart", "track order", "track your order", "find a store"
        }
        ui_modal_titles = {
            "item added to your cart", "added to your cart", "shopping cart", "your cart", "cart",
            "quick view", "skip to content", "customer reviews", "related products", "you may also like",
            "recently viewed", "filter by", "sort by", "leave a comment", "subscribe to our newsletter",
            "share this product", "close", "menu", "search our store", "my account", "sign in", "create account",
            "order summary", "subtotal", "total", "checkout", "view cart", "continue shopping", "shipping calculated",
            "shipping & returns", "shipping and returns", "size guide", "size chart", "description", "details",
            "materials & care", "materials and care", "how to care", "specifications"
        }
        extracted_description = ""

        # Step 1: Detect Company Name & Legal Identity (Rule 17, 26, 28)
        if not company_name:
            # Pass 1: Site name from meta tags or OpenGraph (<meta property="og:site_name">)
            for p in pages:
                sn = getattr(p.cleaned, "site_name", "")
                if sn and sn.strip().lower() not in generic_titles and len(sn.strip()) > 1:
                    company_name = sn.strip()
                    break

            # Pass 2: JSON-LD Organization or WebSite name
            if not company_name:
                for p in pages:
                    for item in getattr(p.cleaned, "json_ld_data", []):
                        t = item.get("@type", "")
                        types = t if isinstance(t, list) else [t]
                        if any(typ in ["Organization", "Corporation", "LocalBusiness", "Store", "WebSite"] for typ in types):
                            n = item.get("name")
                            if n and isinstance(n, str) and n.strip().lower() not in generic_titles and len(n.strip()) > 1:
                                company_name = n.strip()
                                if item.get("legalName"):
                                    legal_name = str(item.get("legalName")).strip()
                                break
                    if company_name:
                        break

            # Pass 3: Title token matching netloc domain
            # e.g. Domain "shopmanto.com" matches "Manto" in "Comfortable Clothing ... | Manto"
            if not company_name and pages:
                netloc = urllib.parse.urlparse(pages[0].url).netloc.lower().replace("www.", "")
                domain_token = netloc.split(".")[0]  # e.g. "shopmanto" or "zimal"

                for p in pages:
                    if p.cleaned.title:
                        parts = [part.strip() for part in re.split(r"\s*\|\s*|\s+[-–—•]\s+", p.cleaned.title) if part.strip()]
                        for candidate in parts:
                            c_clean = candidate.strip()
                            c_low = c_clean.lower()
                            if c_low not in generic_titles and len(c_clean) > 1:
                                if (len(c_low) >= 3 and c_low in domain_token) or (len(domain_token) >= 3 and domain_token in c_low):
                                    company_name = c_clean
                                    break
                        if company_name:
                            break

            # Pass 4: Standard homepage title prefix or suffix
            if not company_name:
                for p in pages:
                    parsed_path = urllib.parse.urlparse(p.url).path.rstrip("/").lower()
                    if parsed_path == "" and p.cleaned.title:
                        parts = [part.strip() for part in re.split(r"\s*\|\s*|\s+[-–—•]\s+", p.cleaned.title) if part.strip()]
                        if parts:
                            for candidate in [parts[-1], parts[0]]:
                                if candidate.lower() not in generic_titles and 1 < len(candidate) < 40:
                                    company_name = candidate
                                    break
                    if company_name:
                        break

            # Pass 5: Netloc fallback
            if not company_name and pages:
                netloc = urllib.parse.urlparse(pages[0].url).netloc.lower().replace("www.", "")
                company_name = netloc.split(".")[0].capitalize()

        detected_prices = []
        primary_pricing_url = pages[0].url if pages else ""

        # Step 2: Iterate across all crawled pages and extract details
        for p in pages:
            url = p.url
            text = p.cleaned.text
            title = p.cleaned.title
            page_type = getattr(p.cleaned, "page_type", "OTHER")

            # Capture meta description
            if not extracted_description and getattr(p.cleaned, "meta_description", ""):
                extracted_description = p.cleaned.meta_description

            # -------------------------------------------------------------
            # A. Structured Extraction from JSON-LD Schemas (Rule 26)
            # -------------------------------------------------------------
            if hasattr(p.cleaned, "json_ld_data") and p.cleaned.json_ld_data:
                for item in p.cleaned.json_ld_data:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get("@type", "")
                    types = item_type if isinstance(item_type, list) else [item_type]

                    # 1. Product Schemas (Exact catalog item with price & currency)
                    if any(t in ("Product", "IndividualProduct") for t in types):
                        p_name = item.get("name")
                        p_sku = item.get("sku")
                        p_cat = item.get("category") or "Catalog Offering"
                        p_offers = item.get("offers")
                        p_price = None
                        p_curr = None

                        if isinstance(p_offers, dict):
                            p_price = p_offers.get("price")
                            p_curr = p_offers.get("priceCurrency")
                        elif isinstance(p_offers, list) and len(p_offers) > 0 and isinstance(p_offers[0], dict):
                            p_price = p_offers[0].get("price")
                            p_curr = p_offers[0].get("priceCurrency")

                        formatted_price = f"{p_curr} {p_price}" if (p_price and p_curr) else (str(p_price) if p_price else None)
                        if formatted_price:
                            detected_prices.append(formatted_price)

                        if p_name and isinstance(p_name, str):
                            clean_p_name = p_name.strip()
                            if (
                                len(clean_p_name) > 2
                                and clean_p_name.lower() not in generic_titles
                                and clean_p_name.lower() not in ui_modal_titles
                                and not any(o["title"].lower() == clean_p_name.lower() for o in offerings)
                            ):
                                offerings.append({
                                    "title": clean_p_name,
                                    "category": str(p_cat),
                                    "price": formatted_price,
                                    "source_url": url,
                                    "sku": str(p_sku) if p_sku else None
                                })
                                structured_facts.append({
                                    "statement": f"Verified Product '{clean_p_name}'" + (f" priced at {formatted_price}" if formatted_price else ""),
                                    "source_url": url,
                                    "fact_type": "OFFERING",
                                    "confidence": 0.98,
                                    "extracted_at": now_iso
                                })

                    # 2. Organization / LocalBusiness / Store Schemas
                    if any(t in ("Organization", "LocalBusiness", "Store", "Corporation") for t in types):
                        tel = item.get("telephone")
                        if tel and str(tel).strip() not in contact_info["phones"]:
                            contact_info["phones"].append(str(tel).strip())
                            structured_facts.append({
                                "statement": f"Official phone contact: {tel}",
                                "source_url": url,
                                "fact_type": "CONTACT",
                                "confidence": 0.98,
                                "extracted_at": now_iso
                            })

                        em = item.get("email")
                        if em and str(em).strip() not in contact_info["emails"]:
                            contact_info["emails"].append(str(em).strip())
                            structured_facts.append({
                                "statement": f"Official contact email: {em}",
                                "source_url": url,
                                "fact_type": "CONTACT",
                                "confidence": 0.98,
                                "extracted_at": now_iso
                            })

                        addr = item.get("address")
                        if isinstance(addr, dict):
                            addr_parts = [addr.get("streetAddress"), addr.get("addressLocality"), addr.get("postalCode"), addr.get("addressCountry")]
                            addr_str = ", ".join([str(p).strip() for p in addr_parts if p])
                            if addr_str and addr_str not in contact_info["addresses"]:
                                contact_info["addresses"].append(addr_str)
                                structured_facts.append({
                                    "statement": f"Corporate address: {addr_str}",
                                    "source_url": url,
                                    "fact_type": "CONTACT",
                                    "confidence": 0.95,
                                    "extracted_at": now_iso
                                })
                        elif isinstance(addr, str) and addr.strip() and addr.strip() not in contact_info["addresses"]:
                            contact_info["addresses"].append(addr.strip())

                        if not legal_name and item.get("legalName"):
                            legal_name = str(item.get("legalName")).strip()

                    # 3. FAQPage Schemas
                    if any(t == "FAQPage" for t in types):
                        main_entity = item.get("mainEntity", [])
                        if isinstance(main_entity, list):
                            for qa in main_entity:
                                if isinstance(qa, dict):
                                    q = qa.get("name") or qa.get("question")
                                    ans_obj = qa.get("acceptedAnswer") or qa.get("answer")
                                    a = ans_obj.get("text") if isinstance(ans_obj, dict) else (ans_obj if isinstance(ans_obj, str) else "")
                                    if q and a:
                                        clean_a = re.sub(r"<[^>]+>", "", a).strip()
                                        if not any(f["question"].lower() == str(q).strip().lower() for f in faqs):
                                            faqs.append({"question": str(q).strip(), "answer": clean_a[:500], "source_url": url})
                                            structured_facts.append({
                                                "statement": f"FAQ: Q: {str(q).strip()} | A: {clean_a[:150]}...",
                                                "source_url": url,
                                                "fact_type": "FAQ",
                                                "confidence": 0.98,
                                                "extracted_at": now_iso
                                            })

            # -------------------------------------------------------------
            # B. Contact Signals from HTML Text & Meta (Rule 22)
            # -------------------------------------------------------------
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

            # -------------------------------------------------------------
            # C. Approved Call-to-Actions (CTAs)
            # -------------------------------------------------------------
            cta_matches = re.findall(
                r"\b(shop now|buy now|add to cart|order now|contact us|get a quote|schedule demo|explore collection|book appointment)\b",
                text,
                re.I
            )
            for c in cta_matches:
                cta_item = {"action": c.capitalize(), "source_url": url}
                if cta_item not in ctas:
                    ctas.append(cta_item)

            # -------------------------------------------------------------
            # D. Product & Catalog Text Extraction (DOM Fallback)
            # -------------------------------------------------------------
            url_path = urllib.parse.urlparse(url).path.lower()
            is_policy_or_info = page_type in ("LEGAL_POLICY", "FAQ", "CONTACT", "HOME", "ABOUT_US") or any(
                k in url_path for k in ["policy", "policies", "terms", "privacy", "refund", "return", "contact", "about", "faq", "store-locator", "track-order", "rewards", "loyalty"]
            )
            is_catalog_or_product = (
                not is_policy_or_info
                and url_path not in ("", "/")
                and (
                    page_type in ("PRODUCT_CATALOG", "PRODUCT_DETAIL")
                    or any(k in url_path for k in ["/product", "/service", "/collection", "/category", "/catalog", "/item"])
                )
            )
            if is_catalog_or_product:
                title_parts = re.split(r"\s*\|\s*|\s+[-–—•]\s+", title) if title else []
                clean_title = title_parts[0].strip() if title_parts else ""

                if (
                    len(clean_title) > 3
                    and clean_title.lower() not in generic_titles
                    and clean_title.lower() not in ui_modal_titles
                ):
                    item_price_match = re.search(r"(?:Rs\.?|PKR|£|€|₹|\$)\s*\d[\d,]*(?:\.\d{2})?", text, re.I)
                    item_price = item_price_match.group(0).strip() if item_price_match else None
                    if item_price:
                        detected_prices.append(item_price)

                    offering_item = {
                        "title": clean_title,
                        "category": "Products & Apparel" if any(k in url.lower() for k in ["lawn", "suit", "dress", "clothing", "collection", "apparel"]) else "Core Offerings",
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

                # Extract H2 headings as collections or secondary offerings
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
                                "category": "Collection / Category",
                                "source_url": url
                            })

            # -------------------------------------------------------------
            # E. Pricing & Commercials Synthesis (Rule 26)
            # -------------------------------------------------------------
            price_matches = re.findall(r"(?:Rs\.?|PKR|£|€|₹|\$)\s*\d[\d,]*(?:\.\d{2})?", text, re.I)
            if price_matches:
                detected_prices.extend(price_matches[:5])
                if not pricing_data or pricing_data.get("requires_human_review"):
                    primary_pricing_url = url
                    curr = "USD"
                    if any("pkr" in m.lower() or "rs" in m.lower() for m in price_matches):
                        curr = "PKR"
                    elif any("£" in m for m in price_matches):
                        curr = "GBP"
                    elif any("€" in m for m in price_matches):
                        curr = "EUR"
                    elif any("₹" in m for m in price_matches):
                        curr = "INR"

                    free_shipping = re.search(r"free\s+(?:shipping|delivery)\s+(?:on|above|over)?\s*(?:orders\s+)?((?:Rs\.?|PKR|£|€|₹|\$)\s*[\d,]+)", text, re.I)
                    free_ship_str = free_shipping.group(0).strip() if free_shipping else None

                    pricing_data = {
                        "model": "PUBLIC_CATALOG_PRICING" if is_catalog_or_product else "PUBLIC_TIERS",
                        "currency": curr,
                        "detected_signals": [p.strip() for p in price_matches[:10]],
                        "free_shipping_offer": free_ship_str,
                        "source_url": url,
                        "requires_human_review": False
                    }
                    structured_facts.append({
                        "statement": f"Verified Pricing ({curr}): Sample rates {', '.join(price_matches[:4])}" + (f" | {free_ship_str}" if free_ship_str else ""),
                        "source_url": url,
                        "fact_type": "PRICING",
                        "confidence": 0.96,
                        "extracted_at": now_iso
                    })

            # -------------------------------------------------------------
            # F. Value Propositions & Benefits (Rule 26)
            # -------------------------------------------------------------
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

            # -------------------------------------------------------------
            # G. FAQs from DOM Accordions & Q&A Patterns (Rule 26)
            # -------------------------------------------------------------
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

            # -------------------------------------------------------------
            # H. Comprehensive Commercial & Legal Policies (Rule 20 & 26)
            # -------------------------------------------------------------
            is_policy_page = page_type == "LEGAL_POLICY" or any(
                k in url.lower() for k in ["refund", "return", "shipping", "delivery", "policy", "policies", "terms", "warranty"]
            )
            if is_policy_page:
                # 1. Return & Exchange window
                ret_matches = re.finditer(
                    r"(?:exchange|return|refund)[^\.\n]*?(?:within\s+\d+\s+days|\d+\s+days[^\.\n]*?(?:return|exchange|delivery)|unworn|unwashed|original tags|tag intact|receipt)[^\.\n]*",
                    text,
                    re.I
                )
                for m in ret_matches:
                    stmt = m.group(0).strip(" -#*").strip()
                    if 15 < len(stmt) < 180 and not any(pl["policy"].lower() == stmt.lower() for pl in policies):
                        policies.append({"policy": stmt, "category": "Return & Exchange", "source_url": url})
                        structured_facts.append({
                            "statement": f"Return & Exchange Policy: {stmt}",
                            "source_url": url,
                            "fact_type": "POLICY",
                            "confidence": 0.96,
                            "extracted_at": now_iso
                        })

                # 2. Shipping & Delivery timeline
                ship_matches = re.finditer(
                    r"(?:shipping|delivery|dispatch)[^\.\n]*?(?:\d+[\s–-]+\d+\s+(?:working|business|standard)?\s*days|free\s+(?:shipping|delivery)[^\.\n]*|nationwide|cash on delivery|cod)[^\.\n]*",
                    text,
                    re.I
                )
                for m in ship_matches:
                    stmt = m.group(0).strip(" -#*").strip()
                    if 15 < len(stmt) < 180 and not any(pl["policy"].lower() == stmt.lower() for pl in policies):
                        policies.append({"policy": stmt, "category": "Shipping & Delivery", "source_url": url})
                        structured_facts.append({
                            "statement": f"Shipping Policy: {stmt}",
                            "source_url": url,
                            "fact_type": "POLICY",
                            "confidence": 0.96,
                            "extracted_at": now_iso
                        })

                # 3. Order lines directly mentioning policy rules
                for line in text.splitlines():
                    line_s = line.strip("- #*").strip()
                    if (
                        any(w in line_s.lower() for w in ["return", "exchange", "refund", "delivery time", "transit", "cancellation"])
                        and 20 < len(line_s) < 160
                        and not any(pl["policy"].lower() == line_s.lower() for pl in policies)
                    ):
                        policies.append({"policy": line_s, "category": "General Policy", "source_url": url})
                        structured_facts.append({
                            "statement": f"Policy rule: {line_s}",
                            "source_url": url,
                            "fact_type": "POLICY",
                            "confidence": 0.95,
                            "extracted_at": now_iso
                        })

            # -------------------------------------------------------------
            # I. Proof & Metrics
            # -------------------------------------------------------------
            proof_matches = re.findall(r"(\d+%\s+(?:increase|decrease|growth|improvement|reduction|satisfaction|money back)[^.\n]*)", text, re.I)
            for m in proof_matches:
                proof_points.append({"metric": m.strip(), "source_url": url})

            # -------------------------------------------------------------
            # J. Industry Classification
            # -------------------------------------------------------------
            for ind in [
                "Fashion & Apparel", "E-commerce & Retail", "SaaS & Cloud", "Healthcare & Life Sciences",
                "Fintech & Banking", "Manufacturing & Logistics", "Agencies & Consulting", "Real Estate",
                "Education & EdTech", "Consumer Goods"
            ]:
                if re.search(rf"\b{re.escape(ind.split()[0])}\b", text, re.I):
                    industries.add(ind)

        # Fallback values
        if not company_name:
            company_name = "Target Enterprise"

        # Finalize pricing if detected from offerings/products
        if not pricing_data:
            if detected_prices:
                pricing_data = {
                    "model": "PUBLIC_CATALOG_PRICING",
                    "currency": "PKR" if any("rs" in p.lower() or "pkr" in p.lower() for p in detected_prices) else "USD",
                    "detected_signals": list(set(detected_prices))[:10],
                    "source_url": primary_pricing_url,
                    "requires_human_review": False
                }
            else:
                pricing_data = {
                    "model": "CONTACT_SALES",
                    "notes": "No public pricing detected on crawled pages",
                    "requires_human_review": True
                }

        if not extracted_description or len(extracted_description.strip()) < 15:
            if offerings:
                sample_items = ", ".join([o["title"] for o in offerings[:4]])
                final_description = f"{company_name} is an established brand offering {sample_items}."
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
        if pricing_data.get("model") in ("PUBLIC_TIERS", "PUBLIC_CATALOG_PRICING"):
            confidence_calc += 0.10
        else:
            review_reasons.append("Pricing tiers not publicly listed; requires human verification.")
        if len(value_props) >= 2 or len(policies) >= 1:
            confidence_calc += 0.05
        if len(faqs) >= 1 or len(contact_info["emails"]) >= 1 or len(contact_info["phones"]) >= 1:
            confidence_calc += 0.05

        confidence_score = round(min(confidence_calc, 0.98), 2)
        requires_human_review = confidence_score < 0.85 or pricing_data.get("requires_human_review", False)

        return {
            "company_name": company_name,
            "legal_name": legal_name,
            "description": final_description[:600],
            "offerings": offerings[:50],
            "value_propositions": value_props[:15],
            "industries": list(industries) or ["E-commerce & Retail"],
            "icp_hints": {
                "target_customers": "Direct-to-consumer shoppers & wholesale purchasers" if "Fashion & Apparel" in industries else "B2B Decision Makers & Growth Leaders",
                "roles": ["Purchaser", "Head of Sales", "Founder", "Director of Growth", "Category Manager"],
                "company_size": "1-500 employees"
            },
            "pricing": pricing_data,
            "features": features[:25],
            "faqs": faqs[:20],
            "proof": proof_points[:10],
            "policies": policies[:15],
            "contact_info": contact_info,
            "structured_facts": structured_facts[:100],
            "brand_voice": {
                "tone": "Direct, consultative, customer-centric, reliable",
                "formality": "High"
            },
            "claims_policy": {
                "allowed_claims": [p["metric"] for p in proof_points[:3]] or [v["benefit"] for v in value_props[:3]],
                "forbidden_claims": ["Unverified discounts", "Unlimited refunds without product return", "Guaranteed 10x ROI without contract"],
                "policies": policies[:15],
                "contact_info": contact_info,
                "structured_facts": structured_facts[:100],
                "requires_human_review": requires_human_review,
                "review_reasons": review_reasons
            },
            "ctas": ctas[:8] or [{"action": "Explore products and offerings", "source_url": pages[0].url if pages else ""}],
            "confidence_score": confidence_score,
            "requires_human_review": requires_human_review,
            "review_reasons": review_reasons
        }
