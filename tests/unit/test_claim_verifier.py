import pytest
from packages.ai.schemas import OutboundEmailDraft, RecommendedAction
from packages.ai.verifier import ClaimVerifier
from packages.common.models.knowledge import BusinessProfile
from packages.common.models.crm import LeadEnrichment

def test_grounded_claims_pass_verification():
    chunks = [
        "Codenter AI SDR users generate 3.2x more qualified pipeline in 45 days.",
        "Pricing begins at $499/mo with full CRM synchronization."
    ]
    draft = OutboundEmailDraft(
        subject="Scaling outbound pipeline",
        body="Hi Alex, teams adopting Codenter scale qualified pipeline by 3.2x in 45 days.",
        claims_used=["3.2x more qualified pipeline in 45 days"],
        cta="Book a 10-minute demo",
        confidence=0.92
    )

    result = ClaimVerifier.verify_draft(draft, retrieved_chunk_texts=chunks)
    assert result.is_grounded is True
    assert len(result.unsupported_claims) == 0
    assert result.recommended_action == RecommendedAction.SEND
    assert result.confidence == 0.92

def test_ungrounded_claims_trigger_human_review():
    chunks = [
        "Codenter AI SDR users generate 3.2x more qualified pipeline."
    ]
    draft = OutboundEmailDraft(
        subject="Guaranteed 10x ROI",
        body="Hi Alex, our platform guarantees 99.999% revenue lift within 24 hours.",
        claims_used=["99.999% revenue lift within 24 hours"],
        cta="Click here",
        confidence=0.95
    )

    result = ClaimVerifier.verify_draft(draft, retrieved_chunk_texts=chunks)
    assert result.is_grounded is False
    assert len(result.unsupported_claims) == 1
    assert result.recommended_action == RecommendedAction.HUMAN_REVIEW
    assert any("Ungrounded claim" in flag for flag in result.risk_flags)
    assert result.confidence <= 0.70  # Penalized

def test_prohibited_claims_policy_violation():
    chunks = ["Normal facts"]
    bp = BusinessProfile(
        company_name="Acme",
        workspace_id="ws-1",
        claims_policy={"prohibited_claims": ["100% money back guarantee", "free forever"]}
    )
    draft = OutboundEmailDraft(
        subject="Special offer",
        body="We offer a 100% money back guarantee on all SDR services.",
        claims_used=[],
        cta="Join now",
        confidence=0.95
    )

    result = ClaimVerifier.verify_draft(draft, retrieved_chunk_texts=chunks, business_profile=bp)
    assert result.is_grounded is False
    assert "100% money back guarantee" in result.prohibited_claims
    assert result.recommended_action == RecommendedAction.HUMAN_REVIEW
    assert any("Prohibited claim" in flag for flag in result.risk_flags)

def test_fake_research_prevention_without_url():
    chunks = ["Standard facts"]
    draft = OutboundEmailDraft(
        subject="Loved your recent post",
        body="Hi Alex, I saw your recent LinkedIn post about SDR outbound challenges and loved your thoughts.",
        claims_used=[],
        cta="Let's connect",
        confidence=0.92
    )
    # Enrichment has no LinkedIn URL or post provenance
    enrichment = LeadEnrichment(
        workspace_id="ws-1",
        lead_id="lead-1",
        source_urls=["https://acme.org/about"],
        signals_json=["Tech stack: React"]
    )

    result = ClaimVerifier.verify_draft(
        draft,
        retrieved_chunk_texts=chunks,
        lead_enrichment=enrichment
    )
    assert result.fake_research_detected is True
    assert result.recommended_action == RecommendedAction.HUMAN_REVIEW
    assert any("Fabricated prospect research" in flag for flag in result.risk_flags)

def test_confidence_threshold_forces_human_review():
    chunks = ["Valid facts"]
    draft = OutboundEmailDraft(
        subject="Question regarding pipeline",
        body="Hi Alex, reaching out regarding outbound velocity.",
        claims_used=[],
        cta="15 min call",
        confidence=0.75  # Under 0.85 threshold
    )

    result = ClaimVerifier.verify_draft(draft, retrieved_chunk_texts=chunks)
    assert result.confidence == 0.75
    assert result.recommended_action == RecommendedAction.HUMAN_REVIEW
