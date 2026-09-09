import pytest
from pydantic import BaseModel
from packages.ai.gateway import ModelGateway
from packages.ai.schemas import OutboundEmailDraft, RecommendedAction, ModelUsageTelemetry

class SampleSchema(BaseModel):
    greeting: str
    confidence: float

@pytest.mark.asyncio
async def test_model_gateway_offline_structured_generation():
    # Without API keys, gateway produces schema-valid deterministic mock instances
    gateway = ModelGateway()
    draft, telemetry = await gateway.generate_structured(
        system_prompt="You are an SDR assistant.",
        user_prompt="Draft cold outreach to Alex at Acme Corp.",
        schema=OutboundEmailDraft,
        prompt_version="v2.1"
    )

    assert isinstance(draft, OutboundEmailDraft)
    assert draft.subject is not None
    assert len(draft.body) > 10
    assert 0.0 <= draft.confidence <= 1.0
    assert draft.recommended_action in [RecommendedAction.SEND, RecommendedAction.HUMAN_REVIEW]

    assert isinstance(telemetry, ModelUsageTelemetry)
    assert telemetry.prompt_version == "v2.1"
    assert telemetry.total_tokens > 0
    assert telemetry.cost_usd >= 0.0
    assert telemetry.latency_ms >= 0.0

@pytest.mark.asyncio
async def test_model_gateway_auto_fallback_on_primary_failure():
    # Force primary model failure to verify automatic fallback to secondary model
    gateway = ModelGateway(force_fallback_test=True)

    draft, telemetry = await gateway.generate_structured(
        system_prompt="System instructions",
        user_prompt="Generate email draft for pipeline acceleration",
        schema=OutboundEmailDraft,
        model="claude-3-5-sonnet-20241022",
        fallback_model="gpt-4o"
    )

    assert isinstance(draft, OutboundEmailDraft)
    assert telemetry.fallback_triggered is True
    assert telemetry.model == "gpt-4o"

def test_model_gateway_cost_calculation():
    # Claude 3.5 Sonnet: $3 / MTok prompt, $15 / MTok completion
    cost_claude = ModelGateway.calculate_cost("claude-3-5-sonnet-20241022", prompt_tokens=1000, completion_tokens=500)
    assert cost_claude == round((1000 / 1e6 * 3.00) + (500 / 1e6 * 15.00), 6)

    # GPT-4o: $5 / MTok prompt, $15 / MTok completion
    cost_gpt4o = ModelGateway.calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    assert cost_gpt4o == round((1000 / 1e6 * 5.00) + (500 / 1e6 * 15.00), 6)
