"""
Configuration module — loads and validates all environment variables at startup.

All configuration values are exposed as module-level constants so they can be
imported directly:

    from src.config import GROQ_API_KEY, GOOGLE_SHEET_NAME
"""

import logging
import os

from dotenv import load_dotenv

# Load .env file before reading any env vars
load_dotenv()

logger = logging.getLogger(__name__)

# ── Groq API ──────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# Model used for lead analysis; llama3-70b-8192 offers a strong accuracy/speed balance
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ── Google Sheets ─────────────────────────────────────────────────────────────
# Path (absolute or relative) to the service account JSON credentials file
GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
)

# Name of the target spreadsheet; created automatically if it doesn't exist
GOOGLE_SHEET_NAME: str = os.getenv("GOOGLE_SHEET_NAME", "Lead Qualification Results")

# ── Internal constants ────────────────────────────────────────────────────────
# Seconds to wait between API calls to stay within Groq's rate limits
API_RATE_LIMIT_DELAY: float = float(os.getenv("API_RATE_LIMIT_DELAY", "0.5"))

# Seconds for the first retry backoff (doubles each attempt)
API_RETRY_BASE_DELAY: float = float(os.getenv("API_RETRY_BASE_DELAY", "1.0"))

# Maximum number of retry attempts for a failed API call
API_MAX_RETRIES: int = int(os.getenv("API_MAX_RETRIES", "3"))


def validate_config() -> None:
    """
    Validate that all required environment variables are set.

    Raises:
        ValueError: If one or more required variables are missing or empty,
                    listing all missing names in the error message.
    """
    required: dict[str, str] = {
        "GROQ_API_KEY": GROQ_API_KEY,
        "GOOGLE_SHEETS_CREDENTIALS_FILE": GOOGLE_SHEETS_CREDENTIALS_FILE,
        "GOOGLE_SHEET_NAME": GOOGLE_SHEET_NAME,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your credentials."
        )

    logger.debug("Configuration validated — all required variables are present.")
