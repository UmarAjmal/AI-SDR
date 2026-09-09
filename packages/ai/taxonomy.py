import enum
from typing import NamedTuple

class IntentType(str, enum.Enum):
    POSITIVE_INTEREST = "POSITIVE_INTEREST"
    PRICING = "PRICING"
    PRODUCT_QUESTION = "PRODUCT_QUESTION"
    OBJECTION = "OBJECTION"
    REQUEST_INFO = "REQUEST_INFO"
    NOT_INTERESTED = "NOT_INTERESTED"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    WRONG_PERSON = "WRONG_PERSON"
    REFERRAL = "REFERRAL"
    TIMING = "TIMING"
    MEETING_REQUEST = "MEETING_REQUEST"
    HUMAN_REQUEST = "HUMAN_REQUEST"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    AUTO_REPLY = "AUTO_REPLY"

class IntentMetadata(NamedTuple):
    intent: IntentType
    description: str
    can_auto_reply: bool
    requires_human_review: bool
    target_lead_state: str

INTENT_DEFINITIONS: dict[IntentType, IntentMetadata] = {
    IntentType.POSITIVE_INTEREST: IntentMetadata(
        intent=IntentType.POSITIVE_INTEREST,
        description="Prospect expresses clear enthusiasm, asking to connect or learn more",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.PRICING: IntentMetadata(
        intent=IntentType.PRICING,
        description="Prospect asks for pricing, cost, licensing, or subscription tiers",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.PRODUCT_QUESTION: IntentMetadata(
        intent=IntentType.PRODUCT_QUESTION,
        description="Prospect asks technical, capability, integration, or feature questions",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.OBJECTION: IntentMetadata(
        intent=IntentType.OBJECTION,
        description="Prospect raises budget, timing, incumbent vendor, or competition friction",
        can_auto_reply=False,
        requires_human_review=True,
        target_lead_state="REPLIED"
    ),
    IntentType.REQUEST_INFO: IntentMetadata(
        intent=IntentType.REQUEST_INFO,
        description="Prospect asks for case studies, whitepapers, or documentation",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.NOT_INTERESTED: IntentMetadata(
        intent=IntentType.NOT_INTERESTED,
        description="Prospect politely declines without opting out or hostility",
        can_auto_reply=False,
        requires_human_review=False,
        target_lead_state="COMPLETED"
    ),
    IntentType.UNSUBSCRIBE: IntentMetadata(
        intent=IntentType.UNSUBSCRIBE,
        description="Prospect requests to be removed, opted-out, or unsubscribed",
        can_auto_reply=False,
        requires_human_review=False,
        target_lead_state="UNSUBSCRIBED"
    ),
    IntentType.WRONG_PERSON: IntentMetadata(
        intent=IntentType.WRONG_PERSON,
        description="Prospect states they are not the relevant contact person",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.REFERRAL: IntentMetadata(
        intent=IntentType.REFERRAL,
        description="Prospect points to a colleague or alternative contact person",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.TIMING: IntentMetadata(
        intent=IntentType.TIMING,
        description="Prospect asks to circle back in next quarter / next month",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="WAITING"
    ),
    IntentType.MEETING_REQUEST: IntentMetadata(
        intent=IntentType.MEETING_REQUEST,
        description="Prospect agrees to a call or asks for a calendar booking link",
        can_auto_reply=True,
        requires_human_review=False,
        target_lead_state="REPLIED"
    ),
    IntentType.HUMAN_REQUEST: IntentMetadata(
        intent=IntentType.HUMAN_REQUEST,
        description="Prospect asks to speak directly with a human sales representative",
        can_auto_reply=False,
        requires_human_review=True,
        target_lead_state="HANDOFF"
    ),
    IntentType.OUT_OF_SCOPE: IntentMetadata(
        intent=IntentType.OUT_OF_SCOPE,
        description="Reply contains hostile, nonsensical, or legal threat messages",
        can_auto_reply=False,
        requires_human_review=True,
        target_lead_state="HANDOFF"
    ),
    IntentType.AUTO_REPLY: IntentMetadata(
        intent=IntentType.AUTO_REPLY,
        description="Automated Out-of-Office, vacation responder, or delivery failure",
        can_auto_reply=False,
        requires_human_review=False,
        target_lead_state="WAITING"
    )
}
