import pytest
from packages.crm.base import CanonicalContact
from packages.lead_intelligence.scorer import LeadScorer
from packages.common.models.knowledge import BusinessProfile

@pytest.fixture
def mock_business_profile():
    return BusinessProfile(
        id="bp-123",
        workspace_id="ws-123",
        company_name="Codenter AI",
        description="Autonomous AI sales development platform for B2B tech companies",
        offerings=[{"title": "Autonomous SDR Agents"}, {"title": "Multichannel Email Pipeline"}],
        value_propositions=[{"benefit": "Automate outbound prospecting and book qualified meetings"}],
        industries=["SaaS", "Fintech", "Cloud"],
        icp_hints={"employee_ranges": ["50-2500"]},
        is_active=True
    )

def test_hot_enterprise_decision_maker_lead(mock_business_profile):
    lead = CanonicalContact(
        email="alex.mercer@finscale.io",
        first_name="Alex",
        last_name="Mercer",
        phone="+1 (415) 555-9012",
        job_title="VP of Revenue Operations",
        company_name="FinScale Payments",
        domain="finscale.io",
        industry="Fintech",
        employee_count=350,
        lifecycle_stage="salesqualifiedlead",
        lead_notes="Interested in AI SDR demo for next quarter"
    )

    result = LeadScorer.evaluate_lead_score(lead, mock_business_profile)
    assert result.total_score >= 80.0
    assert result.score_band == "HOT"
    assert result.icp_score == 40.0  # Industry match (15) + Employee count (15) + Executive VP title (10)
    assert result.intent_score == 20.0  # SQL stage (20)
    assert result.data_quality_score == 10.0  # Corporate domain (7) + phone (3)
    assert len(result.reasons) >= 4

def test_warm_mid_market_lead(mock_business_profile):
    lead = CanonicalContact(
        email="elena.rostova@datadrive.com",
        first_name="Elena",
        last_name="Rostova",
        job_title="Demand Generation Manager",
        company_name="DataDrive Analytics",
        domain="datadrive.com",
        industry="Data Analytics",
        employee_count=180,
        lifecycle_stage="lead"
    )

    result = LeadScorer.evaluate_lead_score(lead, mock_business_profile)
    assert 50.0 <= result.total_score < 80.0
    assert result.score_band == "WARM"
    assert result.negative_score == 0.0

def test_cold_smb_lead(mock_business_profile):
    lead = CanonicalContact(
        email="bob@bobsplumbing.com",
        first_name="Bob",
        last_name="Smith",
        job_title="Owner",
        company_name="Bob's Local Services",
        domain="bobsplumbing.com",
        industry="Plumbing & HVAC",
        employee_count=4,
        lifecycle_stage="lead"
    )

    result = LeadScorer.evaluate_lead_score(lead, mock_business_profile)
    assert result.total_score < 50.0
    assert result.score_band == "COLD"

def test_personal_free_email_penalty(mock_business_profile):
    lead = CanonicalContact(
        email="john.doe.personal@gmail.com",
        first_name="John",
        last_name="Doe",
        job_title="Sales Consultant",
        company_name="Independent",
        domain="",
        industry="SaaS",
        employee_count=1,
        lifecycle_stage="lead"
    )

    result = LeadScorer.evaluate_lead_score(lead, mock_business_profile)
    assert result.data_quality_score == -10.0
    assert any(r.category == "DATA_QUALITY" and r.points == -10.0 for r in result.reasons)

def test_competitor_and_intern_negative_deductions(mock_business_profile):
    # Case A: Competitor domain match
    comp_lead = CanonicalContact(
        email="sdr.manager@outreach.io",
        first_name="Rick",
        last_name="Sanchez",
        job_title="Director of Sales",
        company_name="Outreach Corp",
        domain="outreach.io",
        industry="SaaS",
        employee_count=1000,
        lifecycle_stage="lead"
    )
    comp_result = LeadScorer.evaluate_lead_score(comp_lead, mock_business_profile)
    assert any(r.category == "NEGATIVE_DEDUCTION" and "competitor" in r.reason.lower() for r in comp_result.reasons)

    # Case B: Intern / student role
    intern_lead = CanonicalContact(
        email="timmy@studentcorp.com",
        first_name="Timmy",
        last_name="Turner",
        job_title="Summer Marketing Intern",
        company_name="Student Corp",
        domain="studentcorp.com",
        industry="SaaS",
        employee_count=50,
        lifecycle_stage="lead"
    )
    intern_result = LeadScorer.evaluate_lead_score(intern_lead, mock_business_profile)
    assert any(r.category == "NEGATIVE_DEDUCTION" and "intern" in r.reason.lower() for r in intern_result.reasons)
    assert intern_result.total_score < 50.0
