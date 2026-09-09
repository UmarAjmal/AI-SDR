import re
import logging
from typing import Optional, Literal
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.crm import CRMLead
from packages.common.models.email import EmailThread, EmailMessage
from packages.common.models.knowledge import BusinessProfile
from packages.common.models.campaign import ConversationEvent
from packages.ai.gateway import ModelGateway

logger = logging.getLogger("codenter.ai.qualification")

class QualificationResult(BaseModel):
    qualification_status: Literal["UNQUALIFIED", "DEVELOPING", "QUALIFIED"]
    fit_score: int = Field(..., ge=0, le=100)
    intent: Literal["LOW", "MEDIUM", "HIGH"]
    need: str
    timing: Literal["NOW", "LATER", "UNKNOWN"]
    authority: Literal["DECISION_MAKER", "INFLUENCER", "UNKNOWN"]
    pain_points: list[str] = Field(default_factory=list)
    next_action: Literal["BOOK_MEETING", "FOLLOW_UP", "HANDOFF", "STOP"]
    reason_codes: list[str] = Field(default_factory=list)

# Over-qualification prevention: pure pleasantries regex
PLEASANTRY_ONLY_REGEX = re.compile(
    r"^(thanks?(\s+you)?|noted|sounds?\s+nice|interesting|have\s+a\s+(good|great)\s+(day|week|weekend)|ok|okay|got\s+it|good\s+luck)[.!]?$",
    re.IGNORECASE
)

class QualificationAgent:
    """
    Autonomous AI Lead Qualification Engine based strictly on the NFAT Framework:
    - Need: Articulated business pain point or operational inefficiency.
    - Fit: Company size, role tier, target industry alignment.
    - Authority: Decision maker, influencer, or end user / intern.
    - Timing: Immediate buying window (NOW), future (LATER), or no interest (UNKNOWN).
    
    Includes hard-coded deterministic safeguards against over-qualifying polite leads.
    """
    @classmethod
    async def evaluate_lead_qualification(
        cls,
        lead: CRMLead,
        thread: Optional[EmailThread] = None,
        thread_history: Optional[str] = None,
        profile: Optional[BusinessProfile] = None,
        gateway: Optional[ModelGateway] = None,
        db: Optional[AsyncSession] = None,
        workspace_id: Optional[str] = None,
        prompt_version: str = "v1.0-nfat-qualification"
    ) -> QualificationResult:
        gw = gateway or ModelGateway()

        # 1. Format full bidirectional conversation history
        if thread_history:
            full_history = thread_history
            latest_inbound = thread_history.split("\n")[-1]
        elif thread is not None:
            if db is not None and getattr(thread, "id", None):
                msg_stmt = select(EmailMessage).where(EmailMessage.thread_id == thread.id).order_by(EmailMessage.created_at.asc())
                res = await db.execute(msg_stmt)
                messages = res.scalars().all()
            else:
                messages = getattr(thread, "messages", None) or []

            history_lines = []
            inbound_texts = []

            for msg in messages:
                direction_val = getattr(msg.direction, "value", str(msg.direction)).upper()
                sender_label = "Prospect" if direction_val == "INBOUND" else "SDR"
                body = (msg.body_text or "").strip()
                history_lines.append(f"[{sender_label}]: {body}")
                if sender_label == "Prospect":
                    inbound_texts.append(body)

            full_history = "\n\n".join(history_lines) if history_lines else f"[Prospect]: {thread.subject}"
            latest_inbound = inbound_texts[-1] if inbound_texts else thread.subject
        else:
            full_history = f"[Prospect]: Lead {lead.first_name} {lead.last_name}"
            latest_inbound = full_history

        # 2. Build NFAT Evaluation System Prompt
        company_name = profile.company_name if profile else "Codenter"
        target_offerings = profile.offerings if profile and profile.offerings else "AI SDR Platform"

        system_prompt = (
            f"You are a Senior Revenue Operations and Lead Qualification AI Analyst representing {company_name}.\n"
            f"Evaluate the prospect conversation strictly against the NFAT Framework:\n"
            "- NEED: Does the prospect state a concrete business pain, challenge, or operational goal that our product solves?\n"
            "- FIT: Does the company and role match our Ideal Customer Profile (0-100 fit score)?\n"
            "- AUTHORITY: Is the contact a DECISION_MAKER (VP, C-level, Founder, Director), INFLUENCER, or UNKNOWN / intern?\n"
            "- TIMING: Active buying window (NOW), deferred (LATER), or non-existent (UNKNOWN)?\n\n"
            "STRICT QUALIFICATION RULE:\n"
            "Only assign 'QUALIFIED' if:\n"
            "1. Need is demonstrated (has concrete pain points).\n"
            "2. Timing is NOW (agrees to meeting, asks for demo, or has active project).\n"
            "3. Authority is DECISION_MAKER or INFLUENCER.\n"
            "If the prospect is merely polite without concrete need, mark 'DEVELOPING' or 'UNQUALIFIED'. Never over-qualify."
        )

        user_prompt = (
            f"LEAD INFORMATION:\n"
            f"- Name: {lead.first_name or ''} {lead.last_name or ''}\n"
            f"- Email: {lead.email}\n"
            f"- Title: {lead.job_title or 'Unknown'}\n"
            f"- Company: {lead.company_name or 'Unknown'}\n"
            f"- Industry: {lead.industry or 'Unknown'}\n"
            f"- Prior ICP Score: {lead.icp_score}\n\n"
            f"CONVERSATION HISTORY:\n"
            f"{full_history}\n\n"
            f"Analyze and output valid JSON matching the QualificationResult schema."
        )

        # 3. Model Gateway Inference
        raw_result, telemetry = await gw.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=QualificationResult,
            workspace_id=lead.workspace_id,
            prompt_version=prompt_version
        )

        # 4. Enforce Hard Deterministic Safeguards against Over-Qualification
        cleaned_inbound = latest_inbound.strip()
        is_pleasantry_only = bool(PLEASANTRY_ONLY_REGEX.match(cleaned_inbound))
        is_intern = bool(re.search(r"\b(intern|student|trainee|assistant)\b", f"{lead.job_title} {cleaned_inbound}", re.IGNORECASE))
        is_explicit_rejection = bool(re.search(r"\b(not\s+interested|no\s+thanks|pass|don't\s+need|do\s+not\s+need)\b", cleaned_inbound, re.IGNORECASE))

        if is_explicit_rejection or is_intern:
            raw_result.qualification_status = "UNQUALIFIED"
            raw_result.intent = "LOW"
            raw_result.next_action = "STOP"
            if is_intern:
                raw_result.authority = "UNKNOWN"
                if "No purchasing authority (intern/student)" not in raw_result.reason_codes:
                    raw_result.reason_codes.append("No purchasing authority (intern/student)")

        elif is_pleasantry_only or (not raw_result.pain_points and raw_result.next_action != "BOOK_MEETING"):
            # Polite lead without demonstrated pain points cannot be marked QUALIFIED
            if raw_result.qualification_status == "QUALIFIED":
                logger.info(f"Over-qualification guard triggered for {lead.email}: demoting to DEVELOPING.")
                raw_result.qualification_status = "DEVELOPING"
                if raw_result.timing == "NOW":
                    raw_result.timing = "UNKNOWN"
                raw_result.reason_codes.append("Over-qualification guard: Polite pleasantry without articulated need")

        # 5. Record Immutable 5-Question Audit Event if DB session available
        if db is not None:
            audit_event = ConversationEvent(
                workspace_id=lead.workspace_id,
                lead_id=lead.id,
                campaign_id=getattr(thread, "campaign_id", None),
                event_type="AI_LEAD_QUALIFICATION",
                rule_matched="NFAT_QUALIFICATION_FRAMEWORK",
                model_version=telemetry.model,
                prompt_version=prompt_version,
                knowledge_chunk_ids=[],
                previous_state=lead.qualification_status,
                new_state=raw_result.qualification_status,
                payload={
                    "qualification_status": raw_result.qualification_status,
                    "fit_score": raw_result.fit_score,
                    "intent": raw_result.intent,
                    "need": raw_result.need,
                    "timing": raw_result.timing,
                    "authority": raw_result.authority,
                    "pain_points": raw_result.pain_points,
                    "next_action": raw_result.next_action,
                    "reason_codes": raw_result.reason_codes,
                    "cost_usd": telemetry.cost_usd
                }
            )
            db.add(audit_event)
            await db.flush()

        return raw_result
