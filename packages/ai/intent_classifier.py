import re
import logging
from typing import Optional

from packages.ai.schemas import IntentClassificationResult
from packages.ai.taxonomy import IntentType, INTENT_DEFINITIONS
from packages.ai.gateway import ModelGateway
from packages.compliance.opt_out_detector import OptOutDetector

logger = logging.getLogger("codenter.ai.classifier")

AUTO_REPLY_REGEX = re.compile(
    r"\b(out\s+of\s+(the\s+)?office|auto(mated)?\s+reply|away\s+from\s+(my\s+)?desk|on\s+annual\s+leave|vacation\s+responder|maternity\s+leave|paternity\s+leave)\b",
    re.IGNORECASE
)

class IntentClassifier:
    """
    Autonomous Inbound Intent Classifier strictly adhering to the 14-intent taxonomy.
    Enforces deterministic opt-out interception before any LLM execution.
    """
    @classmethod
    async def classify_reply(
        cls,
        text: str,
        subject: str = "",
        gateway: Optional[ModelGateway] = None,
        workspace_id: Optional[str] = None
    ) -> IntentClassificationResult:
        full_text = f"{subject}\n{text}".strip()

        # 1. Deterministic Opt-Out Gate (Pre-LLM)
        if OptOutDetector.is_opt_out(full_text):
            matched = OptOutDetector.extract_matched_phrase(full_text)
            logger.info(f"Deterministic opt-out phrase intercepted: '{matched}'. Skipping LLM.")
            return IntentClassificationResult(
                intent=IntentType.UNSUBSCRIBE.value,
                confidence=1.0,
                reasoning=f"Explicit opt-out phrase '{matched}' intercepted by deterministic regex before LLM.",
                suggested_action="Immediate global suppression and campaign sequence halt",
                requires_human_review=False,
                extracted_entities={"matched_phrase": matched}
            )

        # 2. Deterministic Auto-Reply / Out-of-Office Gate (Pre-LLM)
        if AUTO_REPLY_REGEX.search(full_text):
            return IntentClassificationResult(
                intent=IntentType.AUTO_REPLY.value,
                confidence=0.99,
                reasoning="Out-of-office automatic responder detected; no sales intent.",
                suggested_action="Ignore sales sequence progression and re-evaluate later",
                requires_human_review=False
            )

        # 3. LLM Classification via ModelGateway
        gw = gateway or ModelGateway()

        valid_intents = [i.value for i in IntentType]
        system_prompt = (
            "You are an elite Sales Development Intent Classification System.\n"
            f"Classify the prospect reply into EXACTLY ONE of the 14 canonical intents:\n"
            f"{valid_intents}\n\n"
            "GUIDELINES:\n"
            "- POSITIVE_INTEREST: Wants to talk, curious, asks to schedule or learn more.\n"
            "- PRICING: Asks what it costs, tiers, or pricing model.\n"
            "- PRODUCT_QUESTION: Asks specific feature, integration, or compliance questions.\n"
            "- OBJECTION: Mentions budget freeze, bad timing, competitor preference, or lack of need.\n"
            "- REQUEST_INFO: Requests PDF, whitepaper, or documentation.\n"
            "- NOT_INTERESTED: Polite no, not right now, pass.\n"
            "- UNSUBSCRIBE: Stop emailing, remove me.\n"
            "- WRONG_PERSON: Not in charge of this domain.\n"
            "- REFERRAL: Points to another colleague or teammate.\n"
            "- TIMING: Reach back out next month / next quarter.\n"
            "- MEETING_REQUEST: Gives availability or asks for calendar link.\n"
            "- HUMAN_REQUEST: Wants to speak with a human or account executive.\n"
            "- OUT_OF_SCOPE: Aggressive, legal threats, or irrelevant spam.\n"
            "- AUTO_REPLY: Automated away message.\n\n"
            "Return valid JSON matching the schema with confidence (0.0 to 1.0) and thorough reasoning."
        )

        user_prompt = f"Subject: {subject}\n\nProspect Reply:\n{text}"

        result, _ = await gw.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=IntentClassificationResult,
            workspace_id=workspace_id,
            prompt_version="v1.0-intent-classifier"
        )

        # Ensure valid intent
        if result.intent not in valid_intents:
            result.intent = IntentType.PRODUCT_QUESTION.value

        # Enforce human review requirement according to taxonomy
        try:
            intent_enum = IntentType(result.intent)
            metadata = INTENT_DEFINITIONS.get(intent_enum)
            if metadata and metadata.requires_human_review:
                result.requires_human_review = True
            elif result.confidence < 0.85:
                result.requires_human_review = True
        except ValueError:
            result.requires_human_review = True

        return result
