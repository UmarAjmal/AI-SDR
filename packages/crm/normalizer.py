import re
from typing import Any
from packages.crm.base import CanonicalContact

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "mail.com", "zoho.com", "protonmail.com", "proton.me", "live.com"
}

class LeadNormalizer:
    @staticmethod
    def extract_domain_from_email(email: str) -> str | None:
        if not email or "@" not in email:
            return None
        domain = email.split("@")[-1].strip().lower()
        if domain in FREE_EMAIL_DOMAINS:
            return None
        return domain

    @classmethod
    def normalize_hubspot_contact(cls, raw: dict[str, Any]) -> CanonicalContact:
        """
        Normalizes a HubSpot CRM v3 Contact object into CanonicalContact.
        HubSpot contacts have id and properties dict:
        { "id": "123", "properties": { "firstname": "...", ... } }
        """
        props = raw.get("properties", raw)
        record_id = str(raw.get("id") or props.get("hs_object_id") or "")
        
        email = (props.get("email") or "").strip().lower()
        first_name = props.get("firstname") or None
        last_name = props.get("lastname") or None
        phone = props.get("phone") or props.get("mobilephone") or None
        job_title = props.get("jobtitle") or None
        company_name = props.get("company") or None
        
        # Domain: from properties, or fallback to email domain
        domain = props.get("domain") or props.get("website") or None
        if domain:
            domain = re.sub(r"^https?://(www\.)?", "", domain).strip().rstrip("/").lower()
        if not domain:
            domain = cls.extract_domain_from_email(email)

        industry = props.get("industry") or None

        # Employee count parsing
        raw_emp = props.get("numberofemployees") or props.get("numemployees")
        employee_count = None
        if raw_emp:
            try:
                employee_count = int(float(str(raw_emp).replace(",", "").strip()))
            except (ValueError, TypeError):
                pass

        # Location
        city = props.get("city") or ""
        state = props.get("state") or ""
        country = props.get("country") or ""
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) if location_parts else None

        revenue_band = props.get("annualrevenue") or None
        lifecycle_stage = props.get("lifecyclestage") or "lead"
        owner_id = props.get("hubspot_owner_id") or None
        lead_notes = props.get("notes_last_contacted") or props.get("message") or None

        # Suppression & Opt-out
        hs_optout = str(props.get("hs_email_optout", "")).lower() in ("true", "1", "yes")
        unsub_status = str(props.get("hs_lead_status", "")).lower() in ("unsubscribed", "do not contact")
        opt_out = hs_optout or unsub_status or lifecycle_stage == "unsubscribed"
        do_not_contact = opt_out

        # Store extra unmapped properties in custom_fields
        known_keys = {
            "email", "firstname", "lastname", "phone", "mobilephone", "jobtitle",
            "company", "domain", "website", "industry", "numberofemployees", "numemployees",
            "city", "state", "country", "annualrevenue", "lifecyclestage", "hubspot_owner_id",
            "notes_last_contacted", "message", "hs_email_optout", "hs_lead_status", "hs_object_id"
        }
        custom_fields = {k: v for k, v in props.items() if k not in known_keys and v is not None}

        return CanonicalContact(
            crm_record_id=record_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            job_title=job_title,
            company_name=company_name,
            domain=domain,
            industry=industry,
            employee_count=employee_count,
            location=location,
            revenue_band=revenue_band,
            lifecycle_stage=lifecycle_stage,
            owner_id=owner_id,
            lead_notes=lead_notes,
            custom_fields=custom_fields,
            opt_out=opt_out,
            do_not_contact=do_not_contact
        )
