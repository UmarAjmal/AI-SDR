import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from packages.common.models.email import SuppressionList, SuppressionReason
from packages.common.models.crm import CRMLead
from packages.email.suppression import SuppressionChecker

@pytest.mark.asyncio
async def test_exact_email_and_domain_suppression(db_session: AsyncSession):
    workspace_id = "ws-suppression-test"

    # Add exact email suppression
    s1 = SuppressionList(
        workspace_id=workspace_id,
        email="blocked@domain.com",
        reason=SuppressionReason.UNSUBSCRIBE,
        source="INBOUND_REGEX"
    )
    # Add domain wildcard suppression
    s2 = SuppressionList(
        workspace_id=workspace_id,
        domain="competitor.org",
        reason=SuppressionReason.MANUAL,
        source="USER_MANUAL"
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    # Test exact email is suppressed
    assert await SuppressionChecker.is_email_suppressed(workspace_id, "blocked@domain.com", db_session) is True
    # Test other email on domain.com is not suppressed
    assert await SuppressionChecker.is_email_suppressed(workspace_id, "other@domain.com", db_session) is False

    # Test wildcard domain is suppressed
    assert await SuppressionChecker.is_email_suppressed(workspace_id, "ceo@competitor.org", db_session) is True
    assert await SuppressionChecker.is_email_suppressed(workspace_id, "VP_SALES@COMPETITOR.ORG", db_session) is True

    # Test unrelated email is not suppressed
    assert await SuppressionChecker.is_email_suppressed(workspace_id, "friendly@acme.inc", db_session) is False

    # Test lead opt-out check
    lead_opted_out = CRMLead(
        workspace_id=workspace_id,
        email="optout@lead.com",
        opt_out=True,
        do_not_contact=False
    )
    lead_normal = CRMLead(
        workspace_id=workspace_id,
        email="normal@lead.com",
        opt_out=False,
        do_not_contact=False
    )
    db_session.add_all([lead_opted_out, lead_normal])
    await db_session.commit()

    assert await SuppressionChecker.is_lead_opted_out(workspace_id, "optout@lead.com", db_session) is True
    assert await SuppressionChecker.is_lead_opted_out(workspace_id, "normal@lead.com", db_session) is False
