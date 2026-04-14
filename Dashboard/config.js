// ─────────────────────────────────────────────────────────────────────────────
// Dashboard configuration — fill in your values before opening index.html
// ─────────────────────────────────────────────────────────────────────────────
//
// HOW TO GET THESE VALUES:
//
// SPREADSHEET_ID
//   Open your Google Sheet. The URL looks like:
//   https://docs.google.com/spreadsheets/d/ABC123XYZ.../edit
//                                          ^^^^^^^^^^^^
//   Copy the long ID between /d/ and /edit
//
// API_KEY
//   1. Go to https://console.cloud.google.com/
//   2. APIs & Services → Credentials → Create Credentials → API Key
//   3. Restrict it: API restrictions → Google Sheets API only
//   4. Copy the key here
//
// SHEET_NAME
//   The name of the tab inside your spreadsheet (bottom tab label).
//   Default is "Sheet1" — change if you renamed it.
//
// IMPORTANT: Your Google Sheet must be shared as:
//   Share → Anyone with the link → Viewer
//   (The Python script writes via service account; this key only reads)
// ─────────────────────────────────────────────────────────────────────────────

const CONFIG = {
  SPREADSHEET_ID: "1xzQ5FD5R2icSZodAqiQNXwGJBzR5_UggeEZL9vFlGSQ",
  API_KEY: "AIzaSyAwlkBwcpoAWKJWtrGwKagGDHxG3n4O7OA",
  SHEET_NAME: "Sheet1",
};
