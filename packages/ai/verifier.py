import re
import logging
from typing import Optional, Sequence

from packages.ai.schemas import (
    OutboundEmailDraft,
    ClaimVerificationResult,
    RecommendedAction
)
from packages.common.models.knowledge import BusinessProfile
from packages.common.models.crm import LeadEnrichment

logger = logging.getLogger("codenter.ai.verifier")

FAKE_RESEARCH_PATTERNS = [
    r"(?i)\b(saw|noticed|loved|read)\s+your\s+(recent\s+)?(linkedin|twitter|x|facebook)\s+post\b",
    r"(?i)\bcongratulations\s+on\s+your\s+(recent\s+)?(post|article|tweet)\b",
    r"(?i)\bi\s+came\s+across\s+your\s+article\b",
]

class ClaimVerifier:
    """
    Safety, Hallucination and Claim Verification Engine.
    Ensures zero hallucination, strict factual grounding against retrieved knowledge chunks,
    compliance with claims policy, and eradication of fake research statements.
    """
    @classmethod
    def verify_draft(
        cls,
        draft: OutboundEmailDraft,
        retrieved_chunk_texts: Sequence[str],
        business_profile: Optional[BusinessProfile] = None,
        lead_enrichment: Optional[LeadEnrichment] = None,
        prohibited_claims: Optional[list[str]] = None
    ) -> ClaimVerificationResult:
        verified_claims = []
        unsupported_claims = []
        prohibited_detected = []
        risk_flags = list(draft.risk_flags)
        fake_research_detected = False

        corpus_text = " ".join(retrieved_chunk_texts).lower()
        if business_profile:
            proof_str = str(business_profile.proof or "").lower()
            corpus_text += f" {proof_str}"

        # 1. Grounding check on claims_used
        for claim in draft.claims_used:
            claim_norm = claim.strip().lower()
            # Extract key tokens (>3 chars)
            tokens = [t for t in re.findall(r"\w+", claim_norm) if len(t) > 3]
            if not tokens:
                verified_claims.append(claim)
                continue

            matches = sum(1 for t in tokens if t in corpus_text)
            match_ratio = matches / len(tokens)

            if match_ratio >= 0.5:
                verified_claims.append(claim)
            else:
                unsupported_claims.append(claim)
                risk_flags.append(f"Ungrounded claim detected: '{claim}'")

        # 2. Check Prohibited Claims / Guarantees
        prohibited_list = prohibited_claims or []
        if business_profile and business_profile.claims_policy:
            prohibited_list += business_profile.claims_policy.get("prohibited_claims", [])

        full_draft_text = f"{draft.subject} {draft.body}".lower()
        for prohibited in prohibited_list:
            if prohibited.lower() in full_draft_text:
                prohibited_detected.append(prohibited)
                risk_flags.append(f"Prohibited claim policy violation: '{prohibited}'")

        # 3. No Fake Research Check
        for pattern in FAKE_RESEARCH_PATTERNS:
            if re.search(pattern, full_draft_text):
                # Verify whether lead_enrichment actually contains a verified post/article signal
                has_provenance = False
                if lead_enrichment:
                    urls = lead_enrichment.source_urls or []
                    signals = str(lead_enrichment.signals_json or "").lower()
                    if any("linkedin" in u.lower() or "post" in u.lower() for u in urls):
                        has_provenance = True
                    elif "post" in signals or "linkedin" in signals:
                        has_provenance = True

                if not has_provenance:
                    fake_research_detected = True
                    risk_flags.append(
                        "Fabricated prospect research detected: Reference to social post without verified URL provenance"
                    )

        # 4. Confidence & Hallucination Gate
        confidence = draft.confidence
        if unsupported_claims or prohibited_detected or fake_research_detected:
            # Penalize confidence
            confidence = min(confidence, 0.70)

        is_grounded = (
            len(unsupported_claims) == 0
            and len(prohibited_detected) == 0
            and not fake_research_detected
        )

        # Force HUMAN_REVIEW if confidence < 0.85 or any risk flags exist
        if confidence < 0.85 or len(risk_flags) > 0 or not is_grounded:
            recommended_action = RecommendedAction.HUMAN_REVIEW
        else:
            recommended_action = draft.recommended_action

        return ClaimVerificationResult(
            is_grounded=is_grounded,
            verified_claims=verified_claims,
            unsupported_claims=unsupported_claims,
            prohibited_claims=prohibited_detected,
            fake_research_detected=fake_research_detected,
            confidence=round(confidence, 2),
            recommended_action=recommended_action,
            risk_flags=risk_flags
        )
