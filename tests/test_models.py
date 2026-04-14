"""
Unit tests for Pydantic data models.

Tests cover:
- Valid model construction
- Field validation (required fields, value bounds)
- Computed properties (score_category)
- Helper methods (summary, to_sheet_row)
- Edge cases (boundary scores, whitespace stripping)
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import Lead, LeadAnalysis, ProcessedLead


# ── Lead model ─────────────────────────────────────────────────────────────────

class TestLeadModel:
    """Tests for the Lead input model."""

    def test_valid_lead_construction(self):
        lead = Lead(
            name="Sarah Johnson",
            email="sarah@brighttech.io",
            company_name="BrightTech",
            job_title="VP of Sales",
            message="We need CRM automation urgently.",
        )
        assert lead.name == "Sarah Johnson"
        assert lead.email == "sarah@brighttech.io"
        assert lead.company_name == "BrightTech"
        assert lead.job_title == "VP of Sales"

    def test_whitespace_is_stripped(self):
        lead = Lead(
            name="  John Doe  ",
            email="  john@example.com  ",
            company_name="  Acme Corp  ",
            job_title="  CEO  ",
            message="  We need help.  ",
        )
        assert lead.name == "John Doe"
        assert lead.email == "john@example.com"
        assert lead.company_name == "Acme Corp"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            Lead(
                name="John Doe",
                email="john@example.com",
                # company_name, job_title, message all missing
            )

    def test_summary_format(self):
        lead = Lead(
            name="Jane Smith",
            email="jane@co.com",
            company_name="CoolCo",
            job_title="CTO",
            message="Need a solution.",
        )
        assert lead.summary() == "Jane Smith (CTO @ CoolCo)"


# ── LeadAnalysis model ─────────────────────────────────────────────────────────

class TestLeadAnalysisModel:
    """Tests for the LeadAnalysis AI output model."""

    def test_valid_analysis_construction(self):
        analysis = LeadAnalysis(
            lead_score=78,
            industry="SaaS",
            business_need="Needs sales automation to support team growth.",
            recommended_action="Schedule demo call with senior sales rep",
        )
        assert analysis.lead_score == 78
        assert analysis.industry == "SaaS"

    def test_score_zero_is_valid(self):
        analysis = LeadAnalysis(
            lead_score=0,
            industry="Other",
            business_need="No clear need.",
            recommended_action="Disqualify — no fit",
        )
        assert analysis.lead_score == 0

    def test_score_100_is_valid(self):
        analysis = LeadAnalysis(
            lead_score=100,
            industry="Finance",
            business_need="Immediate enterprise deal.",
            recommended_action="Schedule demo call with senior sales rep",
        )
        assert analysis.lead_score == 100

    def test_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            LeadAnalysis(
                lead_score=101,
                industry="SaaS",
                business_need="...",
                recommended_action="...",
            )

    def test_negative_score_raises(self):
        with pytest.raises(ValidationError):
            LeadAnalysis(
                lead_score=-1,
                industry="SaaS",
                business_need="...",
                recommended_action="...",
            )

    def test_score_coerced_from_string(self):
        """The LLM may return lead_score as a string — it should be coerced to int."""
        analysis = LeadAnalysis(
            lead_score="85",   # type: ignore[arg-type]
            industry="Healthcare",
            business_need="Patient data management.",
            recommended_action="Schedule demo call with senior sales rep",
        )
        assert isinstance(analysis.lead_score, int)
        assert analysis.lead_score == 85


# ── ProcessedLead model ────────────────────────────────────────────────────────

class TestProcessedLeadModel:
    """Tests for the ProcessedLead combined model."""

    def _make_processed_lead(self, score: int) -> ProcessedLead:
        return ProcessedLead(
            name="Test User",
            email="test@example.com",
            company_name="TestCo",
            job_title="Manager",
            message="Testing.",
            lead_score=score,
            industry="SaaS",
            business_need="Test need.",
            recommended_action="Test action.",
            processed_at=datetime.now(timezone.utc),
        )

    def test_score_category_high(self):
        assert self._make_processed_lead(70).score_category == "High"
        assert self._make_processed_lead(100).score_category == "High"
        assert self._make_processed_lead(85).score_category == "High"

    def test_score_category_medium(self):
        assert self._make_processed_lead(40).score_category == "Medium"
        assert self._make_processed_lead(55).score_category == "Medium"
        assert self._make_processed_lead(69).score_category == "Medium"

    def test_score_category_low(self):
        assert self._make_processed_lead(0).score_category == "Low"
        assert self._make_processed_lead(15).score_category == "Low"
        assert self._make_processed_lead(39).score_category == "Low"

    def test_score_category_boundary_70(self):
        """Score of exactly 70 should be High, 69 should be Medium."""
        assert self._make_processed_lead(70).score_category == "High"
        assert self._make_processed_lead(69).score_category == "Medium"

    def test_score_category_boundary_40(self):
        """Score of exactly 40 should be Medium, 39 should be Low."""
        assert self._make_processed_lead(40).score_category == "Medium"
        assert self._make_processed_lead(39).score_category == "Low"

    def test_processed_at_defaults_to_utc_now(self):
        """processed_at should be auto-populated when not provided."""
        lead = ProcessedLead(
            name="Auto Time",
            email="auto@example.com",
            company_name="AutoCo",
            job_title="Director",
            message="Checking auto timestamp.",
            lead_score=60,
            industry="Finance",
            business_need="Auto need.",
            recommended_action="Auto action.",
        )
        assert lead.processed_at is not None
        assert lead.processed_at.tzinfo is not None  # Should be timezone-aware

    def test_to_sheet_row_returns_correct_length(self):
        """to_sheet_row() should return exactly 10 values (one per column header)."""
        lead = self._make_processed_lead(75)
        row = lead.to_sheet_row()
        assert len(row) == 10

    def test_to_sheet_row_contains_expected_values(self):
        lead = self._make_processed_lead(75)
        row = lead.to_sheet_row()
        assert row[0] == "Test User"
        assert row[1] == "test@example.com"
        assert row[2] == "TestCo"
        assert row[5] == 75           # lead_score
        assert row[6] == "SaaS"       # industry
        assert "UTC" in row[9]        # processed_at timestamp includes UTC
