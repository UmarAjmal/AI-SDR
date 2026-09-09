from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from packages.common.models.campaign import Campaign, CampaignLead, LeadSequenceState
from packages.common.models.email import EmailMessage, MessageDirection, DeliveryStatus, SuppressionList, SuppressionReason
from packages.common.models.crm import CRMLead
from packages.common.models.calendar import Appointment, AppointmentStatus
from packages.common.models.usage import UsageEvent, UsageEventType
from packages.common.models.telemetry import ConversationEvent, ConversationEventType


class FunnelReport(BaseModel):
    workspace_id: str
    campaign_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # 7-stage Funnel Counts
    enrolled_leads: int = 0
    emails_sent: int = 0
    emails_delivered: int = 0
    replies_received: int = 0
    positive_replies: int = 0
    qualified_leads: int = 0
    meetings_booked: int = 0

    # Negative / Handoff Signals
    bounces: int = 0
    unsubscribes: int = 0
    human_handoffs: int = 0

    # Conversion Rates (0.0 - 100.0%)
    delivery_rate: float = 0.0
    bounce_rate: float = 0.0
    reply_rate: float = 0.0
    positive_reply_rate: float = 0.0
    qualification_rate: float = 0.0
    booking_rate: float = 0.0
    unsubscribe_rate: float = 0.0
    human_handoff_rate: float = 0.0

    # Telemetry & Financial
    total_token_usage: int = 0
    total_spend_usd: float = 0.0
    cost_per_conversation_usd: float = 0.0
    cost_per_meeting_usd: float = 0.0
    average_ai_latency_ms: float = 0.0

    # Breakdowns
    intent_breakdown: Dict[str, int] = Field(default_factory=dict)
    model_token_breakdown: Dict[str, int] = Field(default_factory=dict)


async def get_workspace_funnel(
    workspace_id: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    campaign_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> FunnelReport:
    """
    Computes real-time sales funnel metrics across the 7-stage lifecycle:
    Eligible Leads -> Sends -> Delivered -> Replies -> Positive Replies -> Qualified -> Meetings Booked
    along with conversion rates, AI latencies, token expenditures, and provider costs.
    """
    report = FunnelReport(
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        date_from=date_from,
        date_to=date_to,
    )

    if db is None:
        return report

    # -------------------------------------------------------------
    # 1. ENROLLED LEADS
    # -------------------------------------------------------------
    if campaign_id:
        enrolled_q = select(func.count(CampaignLead.id)).where(CampaignLead.campaign_id == campaign_id)
    else:
        # Leads in any campaign in workspace, or workspace leads
        enrolled_q = (
            select(func.count(CampaignLead.id))
            .join(Campaign, CampaignLead.campaign_id == Campaign.id)
            .where(Campaign.workspace_id == workspace_id)
        )
    res_enrolled = await db.execute(enrolled_q)
    enrolled_count = res_enrolled.scalar_one_or_none() or 0

    if enrolled_count == 0:
        # Fallback to total CRM leads in workspace
        crm_leads_q = select(func.count(CRMLead.id)).where(CRMLead.workspace_id == workspace_id)
        res_crm = await db.execute(crm_leads_q)
        enrolled_count = res_crm.scalar_one_or_none() or 0

    # Also check ConversationEvent for ENROLLED signals if any
    report.enrolled_leads = enrolled_count

    # -------------------------------------------------------------
    # 2. CONVERSATION EVENTS AGGREGATION (High-speed Telemetry)
    # -------------------------------------------------------------
    ce_filters = [ConversationEvent.workspace_id == workspace_id]
    if campaign_id:
        ce_filters.append(ConversationEvent.campaign_id == campaign_id)
    if date_from:
        ce_filters.append(ConversationEvent.created_at >= date_from)
    if date_to:
        ce_filters.append(ConversationEvent.created_at <= date_to)

    ce_q = select(ConversationEvent).where(and_(*ce_filters))
    ce_res = await db.execute(ce_q)
    events = ce_res.scalars().all()

    ce_sends = 0
    ce_inbounds = 0
    ce_positives = 0
    ce_qualified = 0
    ce_booked = 0
    ce_unsubscribes = 0
    ce_handoffs = 0
    latencies = []
    intent_counts: Dict[str, int] = {}

    for ev in events:
        etype = ev.event_type
        payload = ev.data_payload or {}

        if etype in ("EMAIL_SENT", ConversationEventType.EMAIL_SENT.value):
            ce_sends += 1
        elif etype in ("INBOUND_RECEIVED", ConversationEventType.INBOUND_RECEIVED.value):
            ce_inbounds += 1
        elif etype in ("INTENT_CLASSIFIED", ConversationEventType.INTENT_CLASSIFIED.value):
            intent = payload.get("intent") or payload.get("intent_category") or "UNKNOWN"
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            if intent in ("POSITIVE_INTEREST", "MEETING_REQUEST") or payload.get("is_positive") is True:
                ce_positives += 1
        elif etype in ("REPLY_GENERATED", ConversationEventType.REPLY_GENERATED.value):
            intent = payload.get("intent")
            if intent in ("POSITIVE_INTEREST", "MEETING_REQUEST"):
                ce_positives += 1
        elif etype in ("LEAD_QUALIFIED", ConversationEventType.LEAD_QUALIFIED.value):
            ce_qualified += 1
        elif etype in ("MEETING_BOOKED", ConversationEventType.MEETING_BOOKED.value):
            ce_booked += 1
        elif etype in ("OPT_OUT_DETECTED", ConversationEventType.OPT_OUT_DETECTED.value):
            ce_unsubscribes += 1
        elif etype in ("HANDOFF_TRIGGERED", ConversationEventType.HANDOFF_TRIGGERED.value):
            ce_handoffs += 1

        latency = payload.get("latency_ms")
        if latency is not None and isinstance(latency, (int, float)) and latency > 0:
            latencies.append(float(latency))

    # -------------------------------------------------------------
    # 3. EMAILS SENT & DELIVERED & BOUNCED
    # -------------------------------------------------------------
    msg_filters = [EmailMessage.workspace_id == workspace_id]
    if date_from:
        msg_filters.append(EmailMessage.created_at >= date_from)
    if date_to:
        msg_filters.append(EmailMessage.created_at <= date_to)

    # Sent outbound messages
    sent_q = select(func.count(EmailMessage.id)).where(
        and_(*msg_filters, EmailMessage.direction == MessageDirection.OUTBOUND)
    )
    res_sent = await db.execute(sent_q)
    entity_sent = res_sent.scalar_one_or_none() or 0
    report.emails_sent = max(entity_sent, ce_sends)

    # Bounces
    bounced_q = select(func.count(EmailMessage.id)).where(
        and_(*msg_filters, EmailMessage.delivery_status == DeliveryStatus.BOUNCED)
    )
    res_bounced = await db.execute(bounced_q)
    report.bounces = res_bounced.scalar_one_or_none() or 0

    # Delivered messages
    delivered_q = select(func.count(EmailMessage.id)).where(
        and_(*msg_filters, EmailMessage.delivery_status == DeliveryStatus.DELIVERED)
    )
    res_delivered = await db.execute(delivered_q)
    entity_delivered = res_delivered.scalar_one_or_none() or 0

    if entity_delivered > 0:
        report.emails_delivered = entity_delivered
    else:
        # Default delivered = sent - bounces
        report.emails_delivered = max(0, report.emails_sent - report.bounces)

    # -------------------------------------------------------------
    # 4. REPLIES RECEIVED & POSITIVE REPLIES
    # -------------------------------------------------------------
    inbound_q = select(func.count(EmailMessage.id)).where(
        and_(*msg_filters, EmailMessage.direction == MessageDirection.INBOUND)
    )
    res_inbound = await db.execute(inbound_q)
    entity_inbound = res_inbound.scalar_one_or_none() or 0
    report.replies_received = max(entity_inbound, ce_inbounds)
    report.positive_replies = ce_positives

    # -------------------------------------------------------------
    # 5. QUALIFIED LEADS
    # -------------------------------------------------------------
    qual_filters = [
        CRMLead.workspace_id == workspace_id,
        or_(CRMLead.is_qualified == True, CRMLead.qualification_status == "QUALIFIED")  # noqa: E712
    ]
    qual_q = select(func.count(CRMLead.id)).where(and_(*qual_filters))
    res_qual = await db.execute(qual_q)
    entity_qual = res_qual.scalar_one_or_none() or 0
    report.qualified_leads = max(entity_qual, ce_qualified)

    # -------------------------------------------------------------
    # 6. MEETINGS BOOKED
    # -------------------------------------------------------------
    appt_filters = [
        Appointment.workspace_id == workspace_id,
        Appointment.status != AppointmentStatus.CANCELLED
    ]
    if date_from:
        appt_filters.append(Appointment.created_at >= date_from)
    if date_to:
        appt_filters.append(Appointment.created_at <= date_to)

    appt_q = select(func.count(Appointment.id)).where(and_(*appt_filters))
    res_appt = await db.execute(appt_q)
    entity_booked = res_appt.scalar_one_or_none() or 0
    report.meetings_booked = max(entity_booked, ce_booked)

    # -------------------------------------------------------------
    # 7. NEGATIVE / HANDOFF SIGNALS
    # -------------------------------------------------------------
    supp_q = select(func.count(SuppressionList.id)).where(
        SuppressionList.workspace_id == workspace_id,
        SuppressionList.reason == SuppressionReason.UNSUBSCRIBE
    )
    res_supp = await db.execute(supp_q)
    entity_unsubs = res_supp.scalar_one_or_none() or 0
    report.unsubscribes = max(entity_unsubs, ce_unsubscribes)
    report.human_handoffs = ce_handoffs

    # -------------------------------------------------------------
    # 8. USAGE & FINANCIAL TELEMETRY
    # -------------------------------------------------------------
    usage_filters = [UsageEvent.workspace_id == workspace_id]
    if date_from:
        usage_filters.append(UsageEvent.created_at >= date_from)
    if date_to:
        usage_filters.append(UsageEvent.created_at <= date_to)

    usage_q = select(UsageEvent).where(and_(*usage_filters))
    res_usage = await db.execute(usage_q)
    usage_events = res_usage.scalars().all()

    total_tokens = 0
    total_spend = Decimal("0.000000")
    model_breakdown: Dict[str, int] = {}

    for ue in usage_events:
        total_spend += ue.cost_estimate_usd
        meta = ue.metadata_json or {}
        model_name = meta.get("model") or "other"

        if ue.event_type == UsageEventType.MODEL_TOKENS:
            total_tokens += ue.units
            model_breakdown[model_name] = model_breakdown.get(model_name, 0) + ue.units

        lat = meta.get("latency_ms")
        if lat is not None and isinstance(lat, (int, float)) and lat > 0:
            latencies.append(float(lat))

    report.total_token_usage = total_tokens
    report.total_spend_usd = float(round(total_spend, 4))
    report.model_token_breakdown = model_breakdown
    report.intent_breakdown = intent_counts

    # -------------------------------------------------------------
    # 9. CONVERSION RATES COMPUTATION (Percentages 0.0 - 100.0%)
    # -------------------------------------------------------------
    # Delivery Rate: Delivered / Sent
    if report.emails_sent > 0:
        report.delivery_rate = round((report.emails_delivered / report.emails_sent) * 100, 2)
        report.bounce_rate = round((report.bounces / report.emails_sent) * 100, 2)
    else:
        report.delivery_rate = 0.0
        report.bounce_rate = 0.0

    # Reply Rate: Replies / Delivered (or Sent if delivered is 0)
    base_for_replies = report.emails_delivered if report.emails_delivered > 0 else report.emails_sent
    if base_for_replies > 0:
        report.reply_rate = round((report.replies_received / base_for_replies) * 100, 2)
    else:
        report.reply_rate = 0.0

    # Positive Reply Rate: Positive Replies / Replies
    if report.replies_received > 0:
        report.positive_reply_rate = round((report.positive_replies / report.replies_received) * 100, 2)
        report.human_handoff_rate = round((report.human_handoffs / report.replies_received) * 100, 2)
    else:
        report.positive_reply_rate = 0.0
        report.human_handoff_rate = 0.0

    # Qualification Rate: Qualified / Enrolled
    if report.enrolled_leads > 0:
        report.qualification_rate = round((report.qualified_leads / report.enrolled_leads) * 100, 2)
    else:
        report.qualification_rate = 0.0

    # Booking Rate: Booked / Qualified (or Booked / Positive Replies)
    if report.qualified_leads > 0:
        report.booking_rate = round((report.meetings_booked / report.qualified_leads) * 100, 2)
    elif report.positive_replies > 0:
        report.booking_rate = round((report.meetings_booked / report.positive_replies) * 100, 2)
    elif report.enrolled_leads > 0:
        report.booking_rate = round((report.meetings_booked / report.enrolled_leads) * 100, 2)
    else:
        report.booking_rate = 0.0

    # Unsubscribe Rate: Unsubscribes / Delivered
    if base_for_replies > 0:
        report.unsubscribe_rate = round((report.unsubscribes / base_for_replies) * 100, 2)
    else:
        report.unsubscribe_rate = 0.0

    # Average AI Latency
    if latencies:
        report.average_ai_latency_ms = round(sum(latencies) / len(latencies), 1)
    else:
        report.average_ai_latency_ms = 0.0

    # Unit Costs
    if report.replies_received > 0:
        report.cost_per_conversation_usd = round(report.total_spend_usd / report.replies_received, 4)
    else:
        report.cost_per_conversation_usd = 0.0

    if report.meetings_booked > 0:
        report.cost_per_meeting_usd = round(report.total_spend_usd / report.meetings_booked, 4)
    else:
        report.cost_per_meeting_usd = 0.0

    return report
