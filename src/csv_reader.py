"""
CSV reader module — loads and validates the input leads file using pandas.

Column names in the CSV are case-insensitive and may use spaces or underscores.
Rows that fail Pydantic validation are logged and skipped rather than crashing
the entire pipeline.
"""

import logging
from pathlib import Path
from typing import List

import pandas as pd

from src.models import Lead

logger = logging.getLogger(__name__)

# The exact column names the pipeline expects (after normalisation)
REQUIRED_COLUMNS: list[str] = [
    "name",
    "email",
    "company_name",
    "job_title",
    "message",
]


class CSVReader:
    """
    Reads a CSV file of sales leads and returns a list of validated Lead objects.

    Column names are normalised to lowercase with spaces replaced by underscores,
    so the source CSV can use "Company Name", "company_name", or "COMPANY NAME"
    interchangeably.
    """

    def __init__(self, file_path: str) -> None:
        """
        Args:
            file_path: Path to the CSV file (absolute or relative).
        """
        self.file_path = Path(file_path)

    def load(self) -> List[Lead]:
        """
        Read and validate the CSV file.

        Returns:
            A list of Lead objects for every valid row in the file.

        Raises:
            FileNotFoundError: If the file does not exist at the given path.
            ValueError: If required columns are missing from the CSV.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Input CSV not found: '{self.file_path}'. "
                "Check the --input path and try again."
            )

        try:
            df = pd.read_csv(self.file_path, dtype=str, keep_default_na=False)
        except Exception as exc:
            raise ValueError(f"Failed to parse CSV file '{self.file_path}': {exc}") from exc

        df = self._normalise_columns(df)
        self._validate_columns(df)

        leads = self._parse_rows(df)
        logger.info(
            "Loaded %d valid lead(s) from '%s' (%d row(s) total).",
            len(leads),
            self.file_path.name,
            len(df),
        )
        return leads

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Lower-case column names and replace spaces/hyphens with underscores."""
        df.columns = (
            df.columns.str.strip().str.lower().str.replace(r"[\s\-]+", "_", regex=True)
        )
        return df

    @staticmethod
    def _validate_columns(df: pd.DataFrame) -> None:
        """Raise ValueError listing any missing required columns."""
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(
                f"CSV is missing required column(s): {', '.join(missing)}. "
                f"Found columns: {', '.join(df.columns.tolist())}"
            )

    @staticmethod
    def _parse_rows(df: pd.DataFrame) -> List[Lead]:
        """
        Iterate over DataFrame rows and build Lead objects.

        Invalid rows are logged at WARNING level and silently skipped.
        """
        leads: List[Lead] = []
        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # +1 for 0-index, +1 for header row
            try:
                lead = Lead(
                    name=row["name"],
                    email=row["email"],
                    company_name=row["company_name"],
                    job_title=row["job_title"],
                    message=row["message"],
                )
                leads.append(lead)
            except Exception as exc:
                logger.warning("Skipping CSV row %d — validation error: %s", row_num, exc)

        return leads
