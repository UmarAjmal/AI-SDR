import re
from typing import Optional, Any
from dataclasses import dataclass, field

from packages.crm.base import CanonicalContact
from packages.common.models.crm import CRMLead
from packages.common.models.knowledge import BusinessProfile

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "aol.com", "mail.com", "zoho.com", "protonmail.com", "proton.me", "live.com"
}

OUT_OF_SCOPE_TITLE_PATTERNS = [
    r"\b(intern|internship|student|academic|graduate student|research assistant|volunteer)\b",
    r"\b(retired|unemployed|seeking opportunities)\b"
]

HIGH_VALUE_TITLE_PATTERNS = [
    r"\b(founder|co-founder|ceo|cro|cmo|cto|coo|cpo|president)\b",
    r"\b(vp|vice president|head of|director|chief)\b.*\b(sales|revenue|growth|marketing|operations|revops|business development|partnerships)\b",
    r"\b(director|head of)\b",
    r"\b(sales director|marketing director|revenue operations|demand gen)\b"
]

@dataclass
class ScoreReason:
    category: str
    points: float
    reason: str

@dataclass
class ScoreResult:
    total_score: float
    score_band: str  # HOT, WARM, COLD
    icp_score: float
    business_relevance_score: float
    intent_score: float
    data_quality_score: float
    negative_score: float
    reasons: list[ScoreReason] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "score_band": self.score_band,
            "icp_score": self.icp_score,
            "business_relevance_score": self.business_relevance_score,
            "intent_score": self.intent_score,
            "data_quality_score": self.data_quality_score,
            "negative_score": self.negative_score,
            "reasons": [{"category": r.category, "points": r.points, "reason": r.reason} for r in self.reasons]
        }

class LeadScorer:
    @classmethod
    def evaluate_lead_score(
        cls,
        lead: CanonicalContact | CRMLead,
        profile: Optional[BusinessProfile] = None
    ) -> ScoreResult:
        reasons: list[ScoreReason] = []

        icp_score = 0.0
        relevance_score = 0.0
        intent_score = 0.0
        quality_score = 0.0
        negative_score = 0.0

        # Helper attributes extraction
        email = (getattr(lead, "email", "") or "").lower().strip()
        job_title = (getattr(lead, "job_title", "") or "").strip()
        company_name = (getattr(lead, "company_name", "") or "").strip()
        domain = (getattr(lead, "domain", "") or "").lower().strip()
        industry = (getattr(lead, "industry", "") or "").strip()
        employee_count = getattr(lead, "employee_count", None)
        lifecycle_stage = (getattr(lead, "lifecycle_stage", "") or "").lower().strip()
        phone = getattr(lead, "phone", None)
        notes = (getattr(lead, "lead_notes", "") or "").lower()

        # 1. ICP FIT (0 to 40 pts)
        # a. Industry Match (0-15 pts)
        target_industries = []
        if profile and profile.industries:
            target_industries = [str(i).lower() for i in profile.industries]
        
        if industry:
            ind_lower = industry.lower()
            if any(t in ind_lower or ind_lower in t for t in target_industries):
                icp_score += 15.0
                reasons.append(ScoreReason("ICP_FIT", 15.0, f"Industry '{industry}' matches target ICP verticals"))
            elif any(k in ind_lower for k in ["software", "tech", "saas", "fintech", "finance", "healthcare", "ecommerce"]):
                icp_score += 10.0
                reasons.append(ScoreReason("ICP_FIT", 10.0, f"Industry '{industry}' is high-affinity B2B vertical"))
            else:
                icp_score += 5.0
                reasons.append(ScoreReason("ICP_FIT", 5.0, f"Industry '{industry}' recorded"))

        # b. Company Size / Employees (0-15 pts)
        if employee_count is not None:
            if 50 <= employee_count <= 2500:
                icp_score += 15.0
                reasons.append(ScoreReason("ICP_FIT", 15.0, f"Employee count ({employee_count}) in ideal sweet spot (50-2500)"))
            elif 2501 <= employee_count <= 10000:
                icp_score += 12.0
                reasons.append(ScoreReason("ICP_FIT", 12.0, f"Upper mid-market company size ({employee_count})"))
            elif 10 <= employee_count < 50:
                icp_score += 8.0
                reasons.append(ScoreReason("ICP_FIT", 8.0, f"Emerging startup/SMB size ({employee_count})"))
            elif employee_count > 10000:
                icp_score += 10.0
                reasons.append(ScoreReason("ICP_FIT", 10.0, f"Large enterprise size ({employee_count})"))
            else:
                icp_score += 3.0
                reasons.append(ScoreReason("ICP_FIT", 3.0, f"Micro-team size ({employee_count})"))

        # c. Job Title & Seniority (0-10 pts)
        if job_title:
            jt_lower = job_title.lower()
            is_out_of_scope = any(re.search(pat, jt_lower) for pat in OUT_OF_SCOPE_TITLE_PATTERNS)
            if not is_out_of_scope:
                is_senior = False
                for pat in HIGH_VALUE_TITLE_PATTERNS:
                    if re.search(pat, jt_lower):
                        icp_score += 10.0
                        reasons.append(ScoreReason("ICP_FIT", 10.0, f"Decision maker / Executive title: '{job_title}'"))
                        is_senior = True
                        break
                if not is_senior:
                    if any(m in jt_lower for m in ["manager", "lead", "specialist", "account executive", "rep"]):
                        icp_score += 6.0
                        reasons.append(ScoreReason("ICP_FIT", 6.0, f"Operational/Mid-tier title: '{job_title}'"))
                    else:
                        icp_score += 3.0
                        reasons.append(ScoreReason("ICP_FIT", 3.0, f"Standard role: '{job_title}'"))

        icp_score = min(40.0, icp_score)

        # 2. BUSINESS RELEVANCE (0 to 25 pts)
        # Check alignment between lead company, industry, or notes with profile offerings
        relevance_score = 10.0  # Base B2B engagement relevance
        relevance_reasons = ["General B2B solution compatibility"]

        if profile:
            profile_texts = []
            if profile.description:
                profile_texts.append(profile.description.lower())
            if profile.offerings:
                for off in profile.offerings:
                    profile_texts.append(str(off).lower())
            if profile.industries:
                for ind in profile.industries:
                    profile_texts.append(str(ind).lower())

            combined_profile = " ".join(profile_texts)
            lead_context = f"{company_name} {industry} {notes}".lower()

            if any(term in combined_profile for term in [industry.lower(), domain]) and industry:
                relevance_score += 10.0
                relevance_reasons.append(f"Domain alignment with core offerings ({industry})")
            if any(term in lead_context for term in ["sdr", "sales", "outreach", "pipeline", "leads", "revenue", "ai"]):
                relevance_score += 5.0
                relevance_reasons.append("High alignment with sales acceleration/AI SDR use case")

        relevance_score = min(25.0, relevance_score)
        reasons.append(ScoreReason("BUSINESS_RELEVANCE", relevance_score, "; ".join(relevance_reasons)))

        # 3. INTENT SIGNALS (0 to 20 pts)
        if lifecycle_stage in ("salesqualifiedlead", "sql"):
            intent_score += 20.0
            reasons.append(ScoreReason("INTENT", 20.0, "Active Sales Qualified Lead (SQL) lifecycle stage"))
        elif lifecycle_stage in ("marketingqualifiedlead", "mql"):
            intent_score += 15.0
            reasons.append(ScoreReason("INTENT", 15.0, "Active Marketing Qualified Lead (MQL) lifecycle stage"))
        elif lifecycle_stage in ("opportunity", "customer"):
            intent_score += 12.0
            reasons.append(ScoreReason("INTENT", 12.0, f"Advanced CRM stage: '{lifecycle_stage}'"))
        elif lifecycle_stage == "lead":
            intent_score += 8.0
            reasons.append(ScoreReason("INTENT", 8.0, "Standard CRM inbound lead stage"))
        else:
            intent_score += 5.0
            reasons.append(ScoreReason("INTENT", 5.0, f"Recorded CRM stage: '{lifecycle_stage}'"))

        if "demo" in notes or "pricing" in notes or "inquiry" in notes:
            added_intent = min(20.0 - intent_score, 5.0)
            if added_intent > 0:
                intent_score += added_intent
                reasons.append(ScoreReason("INTENT", added_intent, "Explicit high-intent inbound notes detected"))

        intent_score = min(20.0, intent_score)

        # 4. DATA QUALITY (0 to 10 pts)
        email_domain = email.split("@")[-1] if "@" in email else ""
        if email_domain in FREE_EMAIL_DOMAINS:
            quality_score -= 10.0
            reasons.append(ScoreReason("DATA_QUALITY", -10.0, f"Personal free email provider (@{email_domain})"))
        else:
            quality_score += 7.0
            reasons.append(ScoreReason("DATA_QUALITY", 7.0, f"Verified corporate domain (@{email_domain})"))
            if phone:
                quality_score += 3.0
                reasons.append(ScoreReason("DATA_QUALITY", 3.0, "Direct phone contact available"))

        # 5. NEGATIVE DEDUCTIONS (-20 to 0 pts)
        # a. Student / Intern out of scope
        if job_title:
            jt_lower = job_title.lower()
            for pat in OUT_OF_SCOPE_TITLE_PATTERNS:
                if re.search(pat, jt_lower):
                    negative_score -= 20.0
                    reasons.append(ScoreReason("NEGATIVE_DEDUCTION", -20.0, f"Out of scope job title / non-decision maker: '{job_title}'"))
                    break

        # b. Competitor check
        competitor_keywords = ["outreach.io", "salesloft", "apollo.io", "gong.io", "zoominfo"]
        if any(c in domain or c in email for c in competitor_keywords):
            negative_score -= 20.0
            reasons.append(ScoreReason("NEGATIVE_DEDUCTION", -20.0, f"Competitor domain identified: '{domain}'"))

        negative_score = max(-20.0, negative_score)

        # TOTAL CLAMPED (0 to 100)
        raw_total = icp_score + relevance_score + intent_score + quality_score + negative_score
        total_score = max(0.0, min(100.0, round(raw_total, 1)))

        # Score Band classification
        if total_score >= 80.0:
            score_band = "HOT"
        elif total_score >= 50.0:
            score_band = "WARM"
        else:
            score_band = "COLD"

        return ScoreResult(
            total_score=total_score,
            score_band=score_band,
            icp_score=round(icp_score, 1),
            business_relevance_score=round(relevance_score, 1),
            intent_score=round(intent_score, 1),
            data_quality_score=round(quality_score, 1),
            negative_score=round(negative_score, 1),
            reasons=reasons
        )
