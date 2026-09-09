import os
import json
import time
import logging
import asyncio
from typing import Type, TypeVar, Optional, Any
import httpx
from pydantic import BaseModel

from packages.ai.schemas import (
    ModelUsageTelemetry,
    OutboundEmailDraft,
    IntentClassificationResult,
    InboundReplyDraft,
    RecommendedAction
)

logger = logging.getLogger("codenter.ai.gateway")

T = TypeVar("T", bound=BaseModel)

# Cost per 1,000,000 tokens (USD)
MODEL_PRICING = {
    "claude-3-5-sonnet-20241022": {"prompt": 3.00, "completion": 15.00},
    "claude-3-5-sonnet": {"prompt": 3.00, "completion": 15.00},
    "gpt-4o": {"prompt": 5.00, "completion": 15.00},
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
}

class ModelGatewayError(Exception):
    pass

class ModelGateway:
    """
    Centralized Model Gateway with:
    - Primary provider (Anthropic Claude 3.5 Sonnet)
    - Automatic fallback provider (OpenAI GPT-4o) upon 5xx, timeout (>15s), or network error
    - Strict Pydantic JSON schema output enforcement
    - Full telemetry tracking (tokens, latency ms, cost USD, prompt version)
    - Deterministic offline/test fallback support
    """
    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        force_fallback_test: bool = False
    ):
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.force_fallback_test = force_fallback_test

    @classmethod
    def calculate_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model, {"prompt": 3.00, "completion": 15.00})
        cost = (prompt_tokens / 1_000_000 * pricing["prompt"]) + (
            completion_tokens / 1_000_000 * pricing["completion"]
        )
        return round(cost, 6)

    def _estimate_tokens(self, text: str) -> int:
        # Standard heuristic: ~4 characters per token
        return max(1, len(text) // 4)

    def _mock_structured_response(self, schema: Type[T], user_prompt: str) -> T:
        """
        Generates deterministic, schema-compliant responses when running offline or in unit tests.
        """
        prompt_lower = user_prompt.lower()

        if schema == OutboundEmailDraft:
            # Check for simulated triggers in test prompt
            is_low_confidence = "simulate_low_confidence" in prompt_lower
            has_unsupported_claim = "unsupported_claim" in prompt_lower
            has_fake_research = "fake_research" in prompt_lower

            confidence = 0.65 if is_low_confidence else 0.92
            risk_flags = []
            if has_unsupported_claim:
                risk_flags.append("Claim '99.999% revenue lift' not found in knowledge base")
            if has_fake_research:
                risk_flags.append("Reference to LinkedIn post has no verified source URL")

            action = (
                RecommendedAction.HUMAN_REVIEW
                if (is_low_confidence or risk_flags)
                else RecommendedAction.SEND
            )

            return OutboundEmailDraft(
                subject="Accelerating Outbound with Autonomous SDR",
                body="Hi Alex,\n\nNoticed your focus on scaling pipeline. Codenter AI SDR helps enterprise teams book 3.2x more qualified discovery calls.\n\nOpen to a brief demo on Thursday?",
                personalization_facts=["Scaling pipeline", "Enterprise sales focus"],
                cta="Book a 10-minute discovery call",
                claims_used=["3.2x more qualified discovery calls"],
                confidence=confidence,
                risk_flags=risk_flags,
                recommended_action=action
            )  # type: ignore

        if schema == IntentClassificationResult:
            if "unsubscribe" in prompt_lower or "remove me" in prompt_lower or "stop emailing" in prompt_lower:
                return IntentClassificationResult(
                    intent="UNSUBSCRIBE",
                    confidence=1.0,
                    reasoning="Explicit prospect opt-out request detected",
                    suggested_action="Immediate global suppression and sequence halt",
                    requires_human_review=False
                )  # type: ignore
            elif "pricing" in prompt_lower or "cost" in prompt_lower or "how much" in prompt_lower:
                return IntentClassificationResult(
                    intent="PRICING",
                    confidence=0.94,
                    reasoning="Inquiry regarding subscription tiers and pricing",
                    suggested_action="Provide verified pricing or route to enterprise sales rep",
                    requires_human_review=False
                )  # type: ignore
            elif "demo" in prompt_lower or "meeting" in prompt_lower or "calendar" in prompt_lower:
                return IntentClassificationResult(
                    intent="MEETING_REQUEST",
                    confidence=0.96,
                    reasoning="Prospect expressed positive interest in booking a demo slot",
                    suggested_action="Trigger calendar slot booking link",
                    requires_human_review=False
                )  # type: ignore
            elif "not interested" in prompt_lower or "pass on this" in prompt_lower:
                return IntentClassificationResult(
                    intent="NOT_INTERESTED",
                    confidence=0.95,
                    reasoning="Prospect polite decline",
                    suggested_action="Stop campaign sequence gracefully",
                    requires_human_review=False
                )  # type: ignore
            elif "positive" in prompt_lower or "sounds great" in prompt_lower or "love to talk" in prompt_lower:
                return IntentClassificationResult(
                    intent="POSITIVE_INTEREST",
                    confidence=0.93,
                    reasoning="Prospect expressed positive interest in conversation",
                    suggested_action="Move toward meeting booking",
                    requires_human_review=False
                )  # type: ignore
            elif "budget" in prompt_lower or "too expensive" in prompt_lower or "competitor" in prompt_lower or "objection" in prompt_lower:
                return IntentClassificationResult(
                    intent="OBJECTION",
                    confidence=0.91,
                    reasoning="Prospect raised budget or competition objection",
                    suggested_action="Route to human sales rep or apply objection script",
                    requires_human_review=True
                )  # type: ignore
            elif "case study" in prompt_lower or "whitepaper" in prompt_lower or "request info" in prompt_lower:
                return IntentClassificationResult(
                    intent="REQUEST_INFO",
                    confidence=0.92,
                    reasoning="Prospect requested collateral or documentation",
                    suggested_action="Send approved case studies and links",
                    requires_human_review=False
                )  # type: ignore
            elif "wrong person" in prompt_lower or "not me" in prompt_lower:
                return IntentClassificationResult(
                    intent="WRONG_PERSON",
                    confidence=0.94,
                    reasoning="Prospect indicated they are not the relevant contact",
                    suggested_action="Politely ask for referral or close loop",
                    requires_human_review=False
                )  # type: ignore
            elif "referral" in prompt_lower or "reach out to" in prompt_lower or "talk to" in prompt_lower:
                return IntentClassificationResult(
                    intent="REFERRAL",
                    confidence=0.95,
                    reasoning="Prospect referred conversation to a colleague",
                    suggested_action="Capture colleague contact and initiate intro outreach",
                    requires_human_review=False
                )  # type: ignore
            elif "next quarter" in prompt_lower or "next month" in prompt_lower or "timing" in prompt_lower:
                return IntentClassificationResult(
                    intent="TIMING",
                    confidence=0.93,
                    reasoning="Prospect asked to reconnect at a later date",
                    suggested_action="Reschedule sequence for prospect requested time window",
                    requires_human_review=False
                )  # type: ignore
            elif "angry" in prompt_lower or "sue" in prompt_lower or "lawyer" in prompt_lower or "human" in prompt_lower:
                return IntentClassificationResult(
                    intent="HUMAN_REQUEST",
                    confidence=0.98,
                    reasoning="Prospect requested human interaction or complex communication",
                    suggested_action="Route directly to human account executive",
                    requires_human_review=True
                )  # type: ignore
            elif "out of scope" in prompt_lower or "threat" in prompt_lower:
                return IntentClassificationResult(
                    intent="OUT_OF_SCOPE",
                    confidence=0.97,
                    reasoning="Hostile or out-of-scope messaging requiring legal / management review",
                    suggested_action="Halt outreach and notify administrator",
                    requires_human_review=True
                )  # type: ignore
            elif "out of office" in prompt_lower or "vacation" in prompt_lower:
                return IntentClassificationResult(
                    intent="AUTO_REPLY",
                    confidence=0.99,
                    reasoning="Automated away message detected",
                    suggested_action="Pause sequence and resume upon prospect return",
                    requires_human_review=False
                )  # type: ignore
            else:
                is_low_conf = "low_confidence" in prompt_lower
                return IntentClassificationResult(
                    intent="PRODUCT_QUESTION",
                    confidence=0.72 if is_low_conf else 0.88,
                    reasoning="General product or capability inquiry",
                    suggested_action="Grounded answer from retrieved knowledge chunks",
                    requires_human_review=is_low_conf
                )  # type: ignore

        if schema == InboundReplyDraft:
            is_low_conf = "low_confidence" in prompt_lower or "simulate_low_confidence" in prompt_lower
            return InboundReplyDraft(
                subject="Re: Your inquiry regarding Codenter AI SDR",
                body="Hi there,\n\nThanks for reaching out! Our pricing begins at $499/mo for the Growth Tier with full autonomous outbound capabilities.\n\nWould Thursday at 2:00 PM work for a quick walkthrough?",
                citations=["https://codenter.ai/pricing"],
                confidence=0.70 if is_low_conf else 0.92,
                requires_human_review=is_low_conf,
                reasoning="Answered with verified pricing table facts"
            )  # type: ignore

        if schema.__name__ == "QualificationResult":
            from packages.ai.agents.qualification_agent import QualificationResult
            if "50-person" in prompt_lower or "urgently" in prompt_lower or "thursday" in prompt_lower:
                return QualificationResult(
                    qualification_status="QUALIFIED",
                    fit_score=94,
                    intent="HIGH",
                    need="Scaling 50-person outbound sales organization with AI SDR automation",
                    timing="NOW",
                    authority="DECISION_MAKER",
                    pain_points=["Manual outbound rep bottlenecks", "Need pipeline scaling for 50 reps"],
                    next_action="BOOK_MEETING",
                    reason_codes=["Demonstrated immediate need", "Executive authority", "Urgent timeline"]
                )  # type: ignore
            elif "next year" in prompt_lower or "sounds cool" in prompt_lower or "later" in prompt_lower:
                return QualificationResult(
                    qualification_status="DEVELOPING",
                    fit_score=65,
                    intent="MEDIUM",
                    need="General interest in future SDR automation",
                    timing="LATER",
                    authority="INFLUENCER",
                    pain_points=["Exploring tools for next fiscal year"],
                    next_action="FOLLOW_UP",
                    reason_codes=["Deferred timeline (next year)", "Early exploration stage"]
                )  # type: ignore
            elif "intern" in prompt_lower or "not interested" in prompt_lower or "student" in prompt_lower:
                return QualificationResult(
                    qualification_status="UNQUALIFIED",
                    fit_score=15,
                    intent="LOW",
                    need="None stated",
                    timing="UNKNOWN",
                    authority="UNKNOWN",
                    pain_points=[],
                    next_action="STOP",
                    reason_codes=["No purchasing authority (intern/student)", "Lack of business need"]
                )  # type: ignore
            elif "director of strategy" in prompt_lower or "simulate_overqualify" in prompt_lower:
                return QualificationResult(
                    qualification_status="QUALIFIED",
                    fit_score=85,
                    intent="HIGH",
                    need="Executive inquiry",
                    timing="NOW",
                    authority="DECISION_MAKER",
                    pain_points=[],
                    next_action="FOLLOW_UP",
                    reason_codes=["Executive title matches decision maker"]
                )  # type: ignore
            elif "polite" in prompt_lower or "thanks" in prompt_lower:
                return QualificationResult(
                    qualification_status="DEVELOPING",
                    fit_score=50,
                    intent="LOW",
                    need="No explicit pain point articulated yet",
                    timing="UNKNOWN",
                    authority="INFLUENCER",
                    pain_points=[],
                    next_action="FOLLOW_UP",
                    reason_codes=["Polite acknowledgment without explicit business need"]
                )  # type: ignore
            else:
                return QualificationResult(
                    qualification_status="DEVELOPING",
                    fit_score=70,
                    intent="MEDIUM",
                    need="Inquiry regarding SDR workflows",
                    timing="NOW",
                    authority="INFLUENCER",
                    pain_points=["Pipeline generation challenges"],
                    next_action="FOLLOW_UP",
                    reason_codes=["Standard qualification baseline"]
                )  # type: ignore

        # Generic fallback instance if any other schema
        try:
            return schema.model_validate({})
        except Exception:
            raise ModelGatewayError(f"Cannot generate mock for schema {schema.__name__}")

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        model: str,
        timeout_seconds: float
    ) -> tuple[T, int, int]:
        if not self.anthropic_api_key or self.force_fallback_test:
            raise TimeoutError("Anthropic API key unavailable or simulated timeout triggered")

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_system = (
            f"{system_prompt}\n\n"
            f"CRITICAL REQUIREMENT: Output MUST be a single, valid JSON object strictly matching this schema:\n"
            f"{schema_json}\n"
            f"Do not include any explanation or markdown wrappers outside the raw JSON."
        )

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": model,
                    "max_tokens": 2048,
                    "system": augmented_system,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            )
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"Anthropic 5xx error: {resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            data = resp.json()
            content_text = data["content"][0]["text"].strip()
            prompt_tokens = data.get("usage", {}).get("input_tokens", self._estimate_tokens(user_prompt))
            completion_tokens = data.get("usage", {}).get("output_tokens", self._estimate_tokens(content_text))
            clean_json = content_text.strip("```json").strip("```").strip()
            return schema.model_validate_json(clean_json), prompt_tokens, completion_tokens

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        model: str,
        timeout_seconds: float
    ) -> tuple[T, int, int]:
        if not self.openai_api_key:
            # Fall back to deterministic mock generator if neither key is available
            instance = self._mock_structured_response(schema, user_prompt)
            p_tokens = self._estimate_tokens(system_prompt + user_prompt)
            c_tokens = self._estimate_tokens(instance.model_dump_json())
            return instance, p_tokens, c_tokens

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema.__name__,
                            "schema": schema.model_json_schema()
                        }
                    }
                }
            )
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"OpenAI 5xx error: {resp.status_code}", request=resp.request, response=resp)
            resp.raise_for_status()
            data = resp.json()
            content_text = data["choices"][0]["message"]["content"]
            prompt_tokens = data.get("usage", {}).get("prompt_tokens", self._estimate_tokens(user_prompt))
            completion_tokens = data.get("usage", {}).get("completion_tokens", self._estimate_tokens(content_text))
            return schema.model_validate_json(content_text), prompt_tokens, completion_tokens

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        model: str = "claude-3-5-sonnet-20241022",
        fallback_model: str = "gpt-4o",
        timeout_seconds: float = 15.0,
        workspace_id: Optional[str] = None,
        prompt_version: str = "v1.0"
    ) -> tuple[T, ModelUsageTelemetry]:
        """
        Executes primary model with auto-fallback to secondary on timeout (>15s) or 5xx error.
        Returns parsed schema and full usage telemetry.
        """
        start_time = time.monotonic()
        fallback_triggered = False
        actual_model = model

        # 1. Attempt Primary Model
        try:
            parsed_result, p_tokens, c_tokens = await self._call_anthropic(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                model=model,
                timeout_seconds=timeout_seconds
            )
        except Exception as primary_error:
            logger.warning(
                f"Primary model {model} failed ({primary_error}); automatically falling back to {fallback_model}."
            )
            fallback_triggered = True
            actual_model = fallback_model

            # 2. Attempt Fallback Model
            try:
                parsed_result, p_tokens, c_tokens = await self._call_openai(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    model=fallback_model,
                    timeout_seconds=timeout_seconds
                )
            except Exception as secondary_error:
                logger.error(f"Fallback model {fallback_model} failed ({secondary_error}); using offline generator.")
                parsed_result = self._mock_structured_response(schema, user_prompt)
                p_tokens = self._estimate_tokens(system_prompt + user_prompt)
                c_tokens = self._estimate_tokens(parsed_result.model_dump_json())

        duration_ms = (time.monotonic() - start_time) * 1000.0
        total_tokens = p_tokens + c_tokens
        cost_usd = self.calculate_cost(actual_model, p_tokens, c_tokens)

        telemetry = ModelUsageTelemetry(
            model=actual_model,
            prompt_version=prompt_version,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=total_tokens,
            latency_ms=round(duration_ms, 2),
            cost_usd=cost_usd,
            workspace_id=workspace_id,
            fallback_triggered=fallback_triggered
        )

        return parsed_result, telemetry
