"""
AI analysis module — sends lead data to the Groq API and parses the structured response.

Each lead is sent in a separate API call. Retry logic with exponential backoff
handles transient failures, and a short delay between calls respects Groq's
rate limits.
"""

import json
import logging
import re
import time
from typing import Any

from groq import Groq, APIConnectionError, APIStatusError, RateLimitError

from src.config import (
    API_MAX_RETRIES,
    API_RATE_LIMIT_DELAY,
    API_RETRY_BASE_DELAY,
    GROQ_API_KEY,
    GROQ_MODEL,
)
from src.lead_scorer import build_analysis_prompt
from src.models import Lead, LeadAnalysis

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are a senior Sales Development Representative (SDR) with over 10 years of B2B "
    "sales experience across SaaS, Healthcare, Finance, and Enterprise software. "
    "Your task is to evaluate inbound sales leads and return a structured JSON qualification "
    "assessment. You must be critical and realistic — not every lead is a good prospect. "
    "Respond with a valid JSON object only. No explanations, no markdown fences, no commentary."
)


class AIAnalyzer:
    """
    Analyses individual sales leads using the Groq LLM API.

    Handles prompt construction, API communication, response parsing,
    Pydantic validation, retry logic, and rate-limit throttling.
    """

    def __init__(self) -> None:
        """Initialise the Groq API client using the key from config."""
        self.client = Groq(api_key=GROQ_API_KEY)
        logger.debug("AIAnalyzer initialised with model '%s'.", GROQ_MODEL)

    def analyze_lead(self, lead: Lead) -> LeadAnalysis:
        """
        Analyse a single lead and return a structured LeadAnalysis.

        Sends the lead data to Groq with a carefully engineered prompt,
        parses the JSON response, and validates it with Pydantic. Retries
        up to API_MAX_RETRIES times with exponential backoff on failure.

        Args:
            lead: The Lead to analyse.

        Returns:
            A validated LeadAnalysis instance.

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        prompt = build_analysis_prompt(lead)
        last_error: Exception | None = None

        for attempt in range(1, API_MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Attempt %d/%d — analysing '%s'.", attempt, API_MAX_RETRIES, lead.name
                )
                raw_content = self._call_api(prompt)
                data = self._extract_json(raw_content)
                analysis = LeadAnalysis(**data)

                logger.debug(
                    "Lead '%s' scored %d (%s).",
                    lead.name,
                    analysis.lead_score,
                    analysis.industry,
                )
                # Throttle to stay within rate limits
                time.sleep(API_RATE_LIMIT_DELAY)
                return analysis

            except (APIConnectionError, APIStatusError, RateLimitError) as exc:
                last_error = exc
                if attempt < API_MAX_RETRIES:
                    backoff = API_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "API error on attempt %d for '%s': %s — retrying in %.1fs.",
                        attempt,
                        lead.name,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)

            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = exc
                if attempt < API_MAX_RETRIES:
                    logger.warning(
                        "Parse error on attempt %d for '%s': %s — retrying.",
                        attempt,
                        lead.name,
                        exc,
                    )

        raise RuntimeError(
            f"Failed to analyse lead '{lead.name}' after {API_MAX_RETRIES} attempt(s). "
            f"Last error: {last_error}"
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _call_api(self, prompt: str) -> str:
        """
        Make a single Groq chat completion request and return the raw text content.

        Args:
            prompt: The user-turn prompt to send.

        Returns:
            The raw string content of the model's response.
        """
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,          # Low temperature for consistent, factual output
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any]:
        """
        Parse JSON from the API response string.

        Tries direct JSON parsing first, then falls back to extracting a JSON
        object from within markdown code fences or raw text, in case the model
        ignores the response_format instruction.

        Args:
            content: Raw string content from the LLM.

        Returns:
            Parsed JSON as a Python dict.

        Raises:
            ValueError: If no valid JSON object can be extracted.
        """
        # Fast path: the response is clean JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Fallback: extract from ```json ... ``` fences
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        # Fallback: extract the first {...} block from anywhere in the text
        raw_obj = re.search(r"\{.*\}", content, re.DOTALL)
        if raw_obj:
            return json.loads(raw_obj.group(0))

        raise ValueError(
            f"No JSON object found in model response. "
            f"First 300 chars: {content[:300]!r}"
        )
