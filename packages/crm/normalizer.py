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

    @classmethod
    def normalize_salesforce_lead(cls, raw: dict[str, Any]) -> CanonicalContact:
        """
        Normalizes a Salesforce REST API Lead SObject into CanonicalContact.
        """
        record_id = str(raw.get("Id") or "")
        email = (raw.get("Email") or "").strip().lower()
        first_name = raw.get("FirstName") or None
        last_name = raw.get("LastName") or None
        phone = raw.get("Phone") or raw.get("MobilePhone") or None
        job_title = raw.get("Title") or None
        company_name = raw.get("Company") or None

        raw_website = raw.get("Website") or None
        domain = None
        if raw_website:
            domain = re.sub(r"^https?://(www\.)?", "", raw_website).strip().rstrip("/").lower()
        if not domain:
            domain = cls.extract_domain_from_email(email)

        industry = raw.get("Industry") or None

        raw_emp = raw.get("NumberOfEmployees")
        employee_count = None
        if raw_emp is not None:
            try:
                employee_count = int(float(str(raw_emp).replace(",", "").strip()))
            except (ValueError, TypeError):
                pass

        city = raw.get("City") or ""
        state = raw.get("State") or ""
        country = raw.get("Country") or ""
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) if location_parts else None

        revenue_band = str(raw.get("AnnualRevenue")) if raw.get("AnnualRevenue") is not None else None
        lifecycle_stage = raw.get("Status") or "Open - Not Contacted"
        owner_id = str(raw.get("OwnerId")) if raw.get("OwnerId") else None
        lead_notes = raw.get("Description") or None

        opt_out = bool(
            raw.get("HasOptedOutOfEmail") is True
            or str(raw.get("HasOptedOutOfEmail", "")).lower() in ("true", "1")
            or "unsub" in lifecycle_stage.lower()
            or "do not contact" in lifecycle_stage.lower()
        )
        do_not_contact = opt_out or bool(raw.get("DoNotCall") is True)

        known_keys = {
            "Id", "Email", "FirstName", "LastName", "Phone", "MobilePhone",
            "Title", "Company", "Website", "Industry", "NumberOfEmployees",
            "City", "State", "Country", "AnnualRevenue", "Status", "OwnerId",
            "Description", "HasOptedOutOfEmail", "DoNotCall", "attributes"
        }
        custom_fields = {k: v for k, v in raw.items() if k not in known_keys and v is not None}

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

    @classmethod
    def normalize_pipedrive_person(cls, raw: dict[str, Any]) -> CanonicalContact:
        """
        Normalizes a Pipedrive Person object into CanonicalContact.
        Pipedrive emails and phones are arrays of {value, primary}.
        """
        record_id = str(raw.get("id") or "")
        
        # Email parsing
        email = ""
        raw_emails = raw.get("email")
        if isinstance(raw_emails, list) and len(raw_emails) > 0:
            for em in raw_emails:
                if isinstance(em, dict) and em.get("primary"):
                    email = (em.get("value") or "").strip().lower()
                    break
            if not email and isinstance(raw_emails[0], dict):
                email = (raw_emails[0].get("value") or "").strip().lower()
            elif not email and isinstance(raw_emails[0], str):
                email = raw_emails[0].strip().lower()
        elif isinstance(raw_emails, str):
            email = raw_emails.strip().lower()

        first_name = raw.get("first_name") or None
        last_name = raw.get("last_name") or None
        if not first_name and not last_name and raw.get("name"):
            parts = str(raw.get("name")).split(" ", 1)
            first_name = parts[0]
            if len(parts) > 1:
                last_name = parts[1]

        # Phone parsing
        phone = None
        raw_phones = raw.get("phone")
        if isinstance(raw_phones, list) and len(raw_phones) > 0:
            for ph in raw_phones:
                if isinstance(ph, dict) and ph.get("primary"):
                    phone = ph.get("value") or None
                    break
            if not phone and isinstance(raw_phones[0], dict):
                phone = raw_phones[0].get("value") or None
            elif not phone and isinstance(raw_phones[0], str):
                phone = raw_phones[0]
        elif isinstance(raw_phones, str):
            phone = raw_phones

        # Org / Company
        company_name = None
        raw_org = raw.get("org_id")
        if isinstance(raw_org, dict):
            company_name = raw_org.get("name")
        elif isinstance(raw_org, str):
            company_name = raw_org
        if not company_name and raw.get("org_name"):
            company_name = raw.get("org_name")

        domain = cls.extract_domain_from_email(email)
        job_title = raw.get("job_title") or raw.get("title") or None
        
        owner_id = None
        raw_owner = raw.get("owner_id")
        if isinstance(raw_owner, dict):
            owner_id = str(raw_owner.get("id") or "")
        elif raw_owner:
            owner_id = str(raw_owner)

        marketing_status = str(raw.get("marketing_status") or "").lower()
        opt_out = marketing_status in ("unsubscribed", "opted_out", "bounced")
        do_not_contact = opt_out

        known_keys = {"id", "name", "first_name", "last_name", "email", "phone", "org_id", "org_name", "owner_id", "marketing_status"}
        custom_fields = {k: v for k, v in raw.items() if k not in known_keys and v is not None}

        return CanonicalContact(
            crm_record_id=record_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            job_title=job_title,
            company_name=company_name,
            domain=domain,
            industry=None,
            employee_count=None,
            location=None,
            revenue_band=None,
            lifecycle_stage="lead",
            owner_id=owner_id,
            lead_notes=None,
            custom_fields=custom_fields,
            opt_out=opt_out,
            do_not_contact=do_not_contact
        )

    @classmethod
    def normalize_zoho_lead(cls, raw: dict[str, Any]) -> CanonicalContact:
        """
        Normalizes a Zoho CRM v3/v6 Lead module object into CanonicalContact.
        """
        record_id = str(raw.get("id") or "")
        email = (raw.get("Email") or "").strip().lower()
        first_name = raw.get("First_Name") or None
        last_name = raw.get("Last_Name") or None
        phone = raw.get("Phone") or raw.get("Mobile") or None
        job_title = raw.get("Designation") or None
        company_name = raw.get("Company") or None

        raw_website = raw.get("Website") or None
        domain = None
        if raw_website:
            domain = re.sub(r"^https?://(www\.)?", "", raw_website).strip().rstrip("/").lower()
        if not domain:
            domain = cls.extract_domain_from_email(email)

        industry = raw.get("Industry") or None
        
        raw_emp = raw.get("No_of_Employees")
        employee_count = None
        if raw_emp is not None:
            try:
                employee_count = int(float(str(raw_emp).replace(",", "").strip()))
            except (ValueError, TypeError):
                pass

        city = raw.get("City") or ""
        state = raw.get("State") or ""
        country = raw.get("Country") or ""
        location_parts = [p for p in [city, state, country] if p]
        location = ", ".join(location_parts) if location_parts else None

        revenue_band = str(raw.get("Annual_Revenue")) if raw.get("Annual_Revenue") is not None else None
        lifecycle_stage = raw.get("Lead_Status") or "Attempted to Contact"
        
        owner_id = None
        raw_owner = raw.get("Owner")
        if isinstance(raw_owner, dict):
            owner_id = str(raw_owner.get("id") or raw_owner.get("name") or "")
        elif raw_owner:
            owner_id = str(raw_owner)

        lead_notes = raw.get("Description") or None
        opt_out = bool(
            raw.get("Email_Opt_Out") is True
            or str(raw.get("Email_Opt_Out", "")).lower() in ("true", "1")
            or "unsub" in str(lifecycle_stage).lower()
        )
        do_not_contact = opt_out

        known_keys = {
            "id", "Email", "First_Name", "Last_Name", "Phone", "Mobile",
            "Designation", "Company", "Website", "Industry", "No_of_Employees",
            "City", "State", "Country", "Annual_Revenue", "Lead_Status",
            "Owner", "Description", "Email_Opt_Out"
        }
        custom_fields = {k: v for k, v in raw.items() if k not in known_keys and v is not None}

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
