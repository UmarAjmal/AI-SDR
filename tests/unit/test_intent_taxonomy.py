import pytest
from packages.ai.taxonomy import IntentType, INTENT_DEFINITIONS
from packages.ai.intent_classifier import IntentClassifier
from packages.compliance.opt_out_detector import OptOutDetector

@pytest.mark.asyncio
async def test_deterministic_pre_llm_opt_out_recall_100_percent():
    """
    CRITICAL CI/CD AI EVALUATION GATE:
    Enforce strictly 100.0% recall on opt-out phrases (zero false negatives).
    Must intercept before calling any LLM.
    """
    opt_out_benchmark = [
        "Please unsubscribe me immediately.",
        "Unsubscribe",
        "Please remove me from your list.",
        "Take me off your list please.",
        "STOP",
        "Stop emailing me.",
        "Stop contacting our company.",
        "Do not contact me again.",
        "Do not email this address.",
        "Please opt out my email.",
        "Leave me alone.",
        "Delete my contact info from your database.",
        "Never email again.",
        "Cease and desist all marketing communications.",
        "Cancel subscription now.",
    ]

    for phrase in opt_out_benchmark:
        # Check raw detector
        assert OptOutDetector.is_opt_out(phrase) is True, f"Failed recall on: '{phrase}'"
        
        # Check IntentClassifier deterministic path
        result = await IntentClassifier.classify_reply(text=phrase, subject="Re: Quick follow up")
        assert result.intent == IntentType.UNSUBSCRIBE.value, f"Expected UNSUBSCRIBE for '{phrase}', got {result.intent}"
        assert result.confidence == 1.0
        assert "deterministic" in result.reasoning.lower()
        assert result.requires_human_review is False

@pytest.mark.asyncio
async def test_deterministic_auto_reply_gate():
    """
    Out of office and vacation responders must be intercepted before LLM.
    """
    ooo_cases = [
        "I am currently out of the office with no access to email until Monday.",
        "Auto reply: I am away from my desk on annual leave.",
        "Out of office: Maternity leave through November.",
        "Automated reply: On annual leave with limited connectivity."
    ]

    for text in ooo_cases:
        result = await IntentClassifier.classify_reply(text=text, subject="Automatic reply: Re: Outbound")
        assert result.intent == IntentType.AUTO_REPLY.value
        assert result.confidence >= 0.95
        assert result.requires_human_review is False

@pytest.mark.asyncio
async def test_intent_taxonomy_classification():
    """
    Verify classification across representative 14-intent taxonomy scenarios.
    """
    test_cases = [
        ("Sounds great, would love to talk more about this!", IntentType.POSITIVE_INTEREST, False),
        ("How much does the Growth tier cost per month? What is your pricing?", IntentType.PRICING, False),
        ("Does your platform support native HubSpot integration?", IntentType.PRODUCT_QUESTION, False),
        ("We have a strict budget freeze and our competitor is cheaper.", IntentType.OBJECTION, True),
        ("Can you send over a case study or whitepaper?", IntentType.REQUEST_INFO, False),
        ("Not interested at this time, please pass on this.", IntentType.NOT_INTERESTED, False),
        ("I am the wrong person for sales tech, not me.", IntentType.WRONG_PERSON, False),
        ("Please reach out to Sarah who manages our SDR team.", IntentType.REFERRAL, False),
        ("Not right now, please reach back out next quarter.", IntentType.TIMING, False),
        ("Let's do a demo on Thursday, send your calendar link.", IntentType.MEETING_REQUEST, False),
        ("I demand to speak with a human account executive immediately.", IntentType.HUMAN_REQUEST, True),
        ("Cease this harassment threat or I will have my attorney file charges out of scope.", IntentType.OUT_OF_SCOPE, True),
    ]

    for text, expected_intent, expected_human_review in test_cases:
        res = await IntentClassifier.classify_reply(text=text, subject="Re: Codenter SDR")
        assert res.intent == expected_intent.value, f"Expected {expected_intent.value} for '{text}', got {res.intent}"
        assert res.requires_human_review == expected_human_review, (
            f"Expected requires_human_review={expected_human_review} for intent {expected_intent.value}"
        )

@pytest.mark.asyncio
async def test_low_confidence_forces_human_review():
    """
    Any reply with classification confidence < 0.85 must require human review.
    """
    text = "Maybe something low_confidence here that is ambiguous."
    res = await IntentClassifier.classify_reply(text=text)
    assert res.confidence < 0.85
    assert res.requires_human_review is True

def test_all_14_intents_have_complete_metadata():
    """
    Assert that all 14 canonical intents in IntentType are registered in INTENT_DEFINITIONS.
    """
    all_intents = list(IntentType)
    assert len(all_intents) == 14

    for intent in all_intents:
        assert intent in INTENT_DEFINITIONS
        meta = INTENT_DEFINITIONS[intent]
        assert meta.intent == intent
        assert isinstance(meta.can_auto_reply, bool)
        assert isinstance(meta.requires_human_review, bool)
        assert isinstance(meta.target_lead_state, str)
