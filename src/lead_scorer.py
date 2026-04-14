"""
Lead scoring module — owns the AI prompt template and score categorisation logic.

Keeping the prompt here (separate from the API call in ai_analyzer.py) means the
scoring criteria can be tuned without touching networking or retry logic.
"""

from typing import Literal

from src.models import Lead

# ── Scoring tiers ─────────────────────────────────────────────────────────────
ScoreCategory = Literal["High", "Medium", "Low"]

SCORE_TIERS: dict[str, tuple[int, int]] = {
    "High": (70, 100),
    "Medium": (40, 69),
    "Low": (0, 39),
}

# ── Prompt template ───────────────────────────────────────────────────────────
_SCORING_GUIDELINES = """\
SCORING CRITERIA
────────────────
80–100 │ Decision-maker (C-Suite, VP, Director), explicit budget signal, clear and
       │ specific business need, urgent timeline, strong company/industry fit.
60–79  │ Mid-level manager (Manager, Senior, Lead), moderate and genuine interest,
       │ some specificity in the message, plausible budget authority, potential fit.
40–59  │ Individual contributor or junior role, some interest but unclear authority,
       │ vague or exploratory message, no confirmed budget or timeline.
20–39  │ Low relevance — personal inquiry, peripheral need, no budget signal,
       │ no clear organisational context or fit.
0–19   │ Spam, student assignment, job seeker, automated bot, or no business context
       │ whatsoever.

RECOMMENDED ACTION GUIDE
────────────────────────
80–100 → "Schedule demo call with senior sales rep"
60–79  → "Send personalised case study and schedule follow-up call"
40–59  → "Add to email nurture sequence"
20–39  → "Send automated introduction email only"
0–19   → "Disqualify — no fit"\
"""

_PROMPT_TEMPLATE = """\
You are a senior Sales Development Representative (SDR) with 10+ years of B2B experience.
Analyse the lead below and return a JSON qualification assessment.

LEAD INFORMATION
────────────────────────────────────────────────────
Name      : {name}
Email     : {email}
Company   : {company_name}
Job Title : {job_title}
Message   : {message}
────────────────────────────────────────────────────

{scoring_guidelines}

INSTRUCTIONS
────────────────────────────────────────────────────
1. Assess seniority and decision-making authority from the job title.
2. Infer company size and industry from the company name and message context.
3. Score the message intent: specific pain points score higher than vague curiosity.
4. Apply the scoring criteria strictly — do not inflate scores.
5. Provide a concise business_need (1–2 sentences max).
6. Pick a recommended_action from the guide above, or write a specific variant if
   the standard options do not fit.

Return ONLY the following JSON object — no markdown, no commentary:

{{
    "lead_score": <integer 0–100>,
    "industry": "<primary industry, e.g. SaaS, Healthcare, E-commerce, Finance, Manufacturing, Education, Real Estate, Logistics, Consulting, Other>",
    "business_need": "<identified or inferred business problem or goal>",
    "recommended_action": "<specific next step for the sales team>"
}}\
"""


def build_analysis_prompt(lead: Lead) -> str:
    """
    Construct the full AI analysis prompt for a given lead.

    Args:
        lead: The Lead instance to build a prompt for.

    Returns:
        A formatted string ready to be sent as the user message to the LLM.
    """
    return _PROMPT_TEMPLATE.format(
        name=lead.name,
        email=lead.email,
        company_name=lead.company_name,
        job_title=lead.job_title,
        message=lead.message,
        scoring_guidelines=_SCORING_GUIDELINES,
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
