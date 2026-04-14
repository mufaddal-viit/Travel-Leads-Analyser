"""
Pydantic data models for the lead qualification pipeline.

Three models form a clean data flow:
  Lead (raw CSV input) → LeadAnalysis (AI output) → ProcessedLead (final record)
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Lead(BaseModel):
    """Represents a raw sales lead parsed from the input CSV."""

    name: str = Field(..., description="Full name of the lead contact")
    email: str = Field(..., description="Email address of the lead")
    company_name: str = Field(..., description="Name of the lead's company or organisation")
    job_title: str = Field(..., description="Lead's job title or role")
    message: str = Field(..., description="Message submitted by the lead via the web form")

    @field_validator("name", "email", "company_name", "job_title", "message", mode="before")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        """Strip leading/trailing whitespace from all string fields."""
        return str(value).strip()

    def summary(self) -> str:
        """Return a one-line human-readable summary of the lead."""
        return f"{self.name} ({self.job_title} @ {self.company_name})"


class LeadAnalysis(BaseModel):
    """AI-generated qualification analysis for a single sales lead."""

    lead_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Lead quality score from 0 (no fit) to 100 (ideal prospect)",
    )
    industry: str = Field(
        ...,
        description="Primary industry category of the lead's company",
    )
    business_need: str = Field(
        ...,
        description="Identified or inferred business problem or goal",
    )
    recommended_action: str = Field(
        ...,
        description="Specific, actionable next step recommended for the sales team",
    )

    @field_validator("lead_score", mode="before")
    @classmethod
    def coerce_score(cls, value: int | str) -> int:
        """Coerce score to int in case the LLM returns it as a string."""
        return int(value)


ScoreCategory = Literal["High", "Medium", "Low"]


class ProcessedLead(BaseModel):
    """
    A fully processed lead that combines raw input data, AI analysis results,
    and processing metadata. This is the final record written to Google Sheets.
    """

    # ── Raw lead fields ──────────────────────────────────────────────────────
    name: str
    email: str
    company_name: str
    job_title: str
    message: str

    # ── AI analysis fields ───────────────────────────────────────────────────
    lead_score: int = Field(..., ge=0, le=100)
    industry: str
    business_need: str
    recommended_action: str

    # ── Metadata ─────────────────────────────────────────────────────────────
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the lead was processed",
    )

    @property
    def score_category(self) -> ScoreCategory:
        """Classify the lead score into a human-readable tier."""
        if self.lead_score >= 70:
            return "High"
        if self.lead_score >= 40:
            return "Medium"
        return "Low"

    def to_sheet_row(self) -> list:
        """Serialize the processed lead to a flat list for Google Sheets insertion."""
        return [
            self.name,
            self.email,
            self.company_name,
            self.job_title,
            self.message,
            self.lead_score,
            self.industry,
            self.business_need,
            self.recommended_action,
            self.processed_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        ]
