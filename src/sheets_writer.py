"""
Google Sheets writer module — appends processed lead records to a spreadsheet.

Authentication uses a Google Cloud service account JSON credentials file.
The spreadsheet is created automatically if it does not already exist, and
headers are written once when a new sheet is first initialised.
"""

import logging
from typing import List

import gspread
from google.oauth2.service_account import Credentials

from src.config import GOOGLE_SHEET_NAME, GOOGLE_SHEETS_CREDENTIALS_FILE
from src.models import ProcessedLead

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes required to read/write Sheets and Drive (for file creation)
_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Column header row — must match the order of ProcessedLead.to_sheet_row()
SHEET_HEADERS: list[str] = [
    "Name",
    "Email",
    "Company",
    "Job Title",
    "Message",
    "Lead Score",
    "Industry",
    "Business Need",
    "Recommended Action",
    "Processed At",
]


class SheetsWriter:
    """
    Manages writing processed leads to a named Google Sheet.

    On initialisation the writer will:
    1. Authenticate with Google using the service account credentials.
    2. Open the target spreadsheet (or create it if missing).
    3. Ensure the header row is present on the first worksheet.
    """

    def __init__(self) -> None:
        """Initialise the Google Sheets client and open or create the target sheet."""
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=_SCOPES
        )
        self.client: gspread.Client = gspread.authorize(creds)
        self.worksheet: gspread.Worksheet = self._get_or_create_worksheet()

    def write_lead(self, processed_lead: ProcessedLead) -> None:
        """
        Append a single processed lead as a new row in the spreadsheet.

        Args:
            processed_lead: The fully analysed lead record to write.
        """
        self.worksheet.append_row(
            processed_lead.to_sheet_row(),
            value_input_option="USER_ENTERED",
        )
        logger.debug(
            "Written '%s' (score=%d) to Google Sheets.",
            processed_lead.name,
            processed_lead.lead_score,
        )

    def write_batch(self, processed_leads: List[ProcessedLead]) -> None:
        """
        Append multiple processed leads in a single API request (more efficient
        than calling write_lead() in a loop for large batches).

        Args:
            processed_leads: List of fully analysed lead records to write.
        """
        if not processed_leads:
            return

        rows = [lead.to_sheet_row() for lead in processed_leads]
        self.worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info("Batch wrote %d lead(s) to Google Sheets.", len(rows))

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_or_create_worksheet(self) -> gspread.Worksheet:
        """
        Open the target spreadsheet, creating it if it doesn't exist, and ensure
        the header row is in place on the first worksheet.

        Returns:
            The gspread Worksheet object ready for writing.
        """
        try:
            spreadsheet = self.client.open(GOOGLE_SHEET_NAME)
            logger.info("Opened existing spreadsheet: '%s'.", GOOGLE_SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            spreadsheet = self.client.create(GOOGLE_SHEET_NAME)
            logger.info("Created new spreadsheet: '%s'.", GOOGLE_SHEET_NAME)

        worksheet = spreadsheet.sheet1
        self._ensure_headers(worksheet)
        return worksheet

    @staticmethod
    def _ensure_headers(worksheet: gspread.Worksheet) -> None:
        """
        Write the header row if it is missing or incorrect.

        Inserts the header at row 1 if data already exists (preserving it),
        or appends to an empty sheet.

        Args:
            worksheet: The worksheet to check and update.
        """
        existing_first_row = worksheet.row_values(1)

        if existing_first_row == SHEET_HEADERS:
            # Headers already correct — nothing to do
            return

        if existing_first_row:
            # Data exists but headers are wrong/missing — insert at top
            worksheet.insert_row(SHEET_HEADERS, index=1)
            logger.info("Inserted header row at top of existing data.")
        else:
            # Sheet is empty — append normally
            worksheet.append_row(SHEET_HEADERS, value_input_option="USER_ENTERED")
            logger.info("Header row written to new sheet.")
