"""
Lead scoring module — score categorisation logic and prompt assembly.

Prompt text lives in src/prompts.py — edit that file to tune scoring criteria
without touching networking or retry logic.
"""

from typing import Literal

from src.models import Lead
from src.prompts import LEAD_PROMPT

# ── Scoring tiers ─────────────────────────────────────────────────────────────
ScoreCategory = Literal["High", "Medium", "Low"]

SCORE_TIERS: dict[str, tuple[int, int]] = {
    "High": (70, 100),
    "Medium": (40, 69),
    "Low": (0, 39),
}


def build_analysis_prompt(lead: Lead) -> str:
    """
    Format the user-turn message for a given lead.

    Args:
        lead: The Lead instance to build a prompt for.

    Returns:
        A formatted string ready to be sent as the user message to the LLM.
    """
    return LEAD_PROMPT.format(
        name=lead.name,
        email=lead.email,
        company_name=lead.company_name,
        job_title=lead.job_title,
        message=lead.message,
    )


def categorize_score(score: int) -> ScoreCategory:
    """
    Map a numeric lead score to its human-readable tier label.

    Args:
        score: Integer score between 0 and 100 (inclusive).

    Returns:
        "High", "Medium", or "Low".
    """
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"
