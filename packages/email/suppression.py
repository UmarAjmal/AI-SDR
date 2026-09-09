from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from packages.common.models.email import SuppressionList, SuppressionReason
from packages.common.models.crm import CRMLead

class SuppressionChecker:
    @classmethod
    async def is_email_suppressed(
        cls,
        workspace_id: str,
        email: str,
        db: AsyncSession
    ) -> bool:
        """
        Determines if an email address is suppressed in the given workspace:
        1. Exact email address match in suppression_list.
        2. Domain-level wildcard match in suppression_list (e.g. competitor.com).
        3. Lead model opt_out or do_not_contact flag.
        """
        if not email or "@" not in email:
            return True

        norm_email = email.strip().lower()
        domain = norm_email.split("@")[-1].strip().lower()

        # 1. Check suppression list by email or domain
        supp_res = await db.execute(
            select(SuppressionList).where(
                SuppressionList.workspace_id == workspace_id,
                or_(
                    SuppressionList.email == norm_email,
                    SuppressionList.domain == domain
                )
            )
        )
        if supp_res.scalar_one_or_none():
            return True

        # 2. Check canonical lead record if exists
        lead_res = await db.execute(
            select(CRMLead).where(
                CRMLead.workspace_id == workspace_id,
                CRMLead.email == norm_email,
                or_(CRMLead.opt_out == True, CRMLead.do_not_contact == True)
            )
        )
        if lead_res.scalar_one_or_none():
            return True

        return False

    @classmethod
    async def is_lead_opted_out(
        cls,
        workspace_id: str,
        email: str,
        db: AsyncSession
    ) -> bool:
        """
        Checks if a lead has manually opted out or flagged do_not_contact.
        """
        norm_email = email.strip().lower()
        lead_res = await db.execute(
            select(CRMLead).where(
                CRMLead.workspace_id == workspace_id,
                CRMLead.email == norm_email,
                or_(CRMLead.opt_out == True, CRMLead.do_not_contact == True)
            )
        )
        return lead_res.scalar_one_or_none() is not None

    @classmethod
    async def add_to_suppression(
        cls,
        workspace_id: str,
        reason: SuppressionReason,
        db: AsyncSession,
        email: Optional[str] = None,
        domain: Optional[str] = None
    ) -> SuppressionList:
        norm_email = email.strip().lower() if email else None
        norm_domain = domain.strip().lower() if domain else None

        if norm_email:
            res = await db.execute(
                select(SuppressionList).where(
                    SuppressionList.workspace_id == workspace_id,
                    SuppressionList.email == norm_email
                )
            )
            existing = res.scalar_one_or_none()
            if existing:
                existing.reason = reason
                await db.commit()
                await db.refresh(existing)
                return existing

        supp = SuppressionList(
            workspace_id=workspace_id,
            email=norm_email,
            domain=norm_domain,
            reason=reason
        )
        db.add(supp)

        # Also propagate to CRMLead if exact email provided
        if norm_email:
            leads_res = await db.execute(
                select(CRMLead).where(
                    CRMLead.workspace_id == workspace_id,
                    CRMLead.email == norm_email
                )
            )
            for l in leads_res.scalars().all():
                l.opt_out = True
                l.do_not_contact = True

        await db.commit()
        await db.refresh(supp)
        return supp
