"""
Reads dashboard credentials from .env and writes Dashboard/config.js.

Usage:
    python generate_dashboard_config.py
    # or
    make dashboard-config

Dashboard/config.js is gitignored — run this once after setting up .env.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Error: python-dotenv is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()

api_key = os.getenv("GOOGLE_SHEETS_API_KEY", "").strip()
spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip()
sheet_name = os.getenv("SHEET_NAME", "Sheet1").strip()

missing = []
if not api_key or api_key == "your_google_sheets_api_key_here":
    missing.append("GOOGLE_SHEETS_API_KEY")
if not spreadsheet_id or spreadsheet_id == "your_spreadsheet_id_here":
    missing.append("SPREADSHEET_ID")

if missing:
    print(f"Error: the following variables are not set in .env: {', '.join(missing)}")
    print("Copy .env.example to .env and fill in the values.")
    sys.exit(1)

config_path = Path(__file__).parent / "Dashboard" / "config.js"

config_js = f"""// AUTO-GENERATED — do not edit manually.
// Run `python generate_dashboard_config.py` (or `make dashboard-config`) to regenerate.
// Source: .env  |  This file is gitignored.

const CONFIG = {{
  SPREADSHEET_ID: "{spreadsheet_id}",
  API_KEY:        "{api_key}",
  SHEET_NAME:     "{sheet_name}",
}};
"""

config_path.write_text(config_js, encoding="utf-8")
print(f"Written: {config_path}")
