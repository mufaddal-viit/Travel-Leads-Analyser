# AI Lead Qualification Automation

A Python automation system that reads inbound sales leads from a CSV file, analyses each one with a Groq-hosted LLM, assigns a lead score and qualification, then writes all results to Google Sheets — fully automated, end-to-end.

---

## Live Dashboard (HTML, JS, CSS)

A browser-based dashboard that reads directly from the same Google Sheet and visualises all processed leads in real time — no server required.

**Open:** [`Dashboard/index.html`](Dashboard/index.html) — double-click in File Explorer or open in any browser.

### Features

| Feature               | Details                                                                      |
| --------------------- | ---------------------------------------------------------------------------- |
| **Live sync**         | Fetches data from Google Sheets API on every load                            |
| **Pagination**        | 50 leads per page — each page is a separate API call                         |
| **Date filter**       | Filter by `Processed At` date range — defaults to today                      |
| **Search**            | Live search across name, company, industry, job title                        |
| **Data source bar**   | Shows sheet name, spreadsheet ID, fetch status, row count, last fetched time |
| **Lead detail modal** | Click any row to see full message, business need, and recommended action     |

### Dashboard Setup

1. Add the following to your `.env` file (see [`.env.example`](.env.example)):
   ```env
   GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key_here
   SPREADSHEET_ID=your_spreadsheet_id_here
   SHEET_NAME=Sheet1
   ```
2. Generate `Dashboard/config.js` from `.env`:
   ```bash
   python generate_dashboard_config.py
   # or
   make dashboard-config
   ```
3. In Google Sheets, click **Share → Anyone with the link → Viewer** (required for the API key to read it).
4. Open [`Dashboard/index.html`](Dashboard/index.html) in a browser.

> `Dashboard/config.js` is gitignored — credentials never touch version control.

> **Note:** The Python pipeline writes to the sheet via a service account (`credentials.json`). The dashboard reads from it via a separate read-only API key. These are two different Google credentials with different purposes.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌────────────────┐     ┌──────────────────┐
│   CSV Input     │────▶│  AI Analysis (Groq)  │────▶│  Lead Scoring  │────▶│  Google Sheets   │
│ sample_leads.csv│     │  llama3-70b-8192     │     │  0–100 score   │     │  Results sheet   │
└─────────────────┘     └──────────────────────┘     └────────────────┘     └──────────────────┘
    csv_reader.py              ai_analyzer.py            lead_scorer.py        sheets_writer.py
                                     │
                              [Retry + Backoff]
                              [Rate limit delay]
```

Each lead passes through a single linear pipeline orchestrated by `src/main.py`:

1. **Load** — `CSVReader` reads and validates the CSV using pandas.
2. **Analyse** — `AIAnalyzer` sends each lead to Groq with a structured prompt and parses the JSON response.
3. **Score** — The LLM returns a score (0–100) guided by explicit scoring criteria in the prompt.
4. **Store** — `SheetsWriter` appends each result to a Google Sheet in real time.

---

## How the AI Prompt Works

Every lead is evaluated through a single Groq API call structured as two messages:

```
┌─────────────────────────────────────────────────────────────────┐
│  SYSTEM MESSAGE  (constant — same for every lead)               │
│                                                                 │
│  • Persona: senior SDR, 10+ years in Travel & Hospitality       │
│  • Scoring signals: Authority, Intent, Fit, Urgency             │
│  • Score ranges with recommended actions (0–19 up to 80–100)    │
│  • Industry categories to classify the lead into                │
│  • Output format: strict JSON, no commentary                    │
└─────────────────────────────────────────────────────────────────┘
                          +
┌─────────────────────────────────────────────────────────────────┐
│  USER MESSAGE  (changes per lead)                               │
│                                                                 │
│  Name      : {name}                                             │
│  Email     : {email}                                            │
│  Company   : {company_name}                                     │
│  Job Title : {job_title}                                        │
│  Message   : {message}                                          │
└─────────────────────────────────────────────────────────────────┘
```

The **system message** is the AI's standing briefing — it never changes between leads. The **user message** is just the lead's raw data. This is the standard pattern for LLM task automation: rules stay in the system prompt, data goes in the user prompt.

<details>
<summary>End-to-end example</summary>

### End-to-end example

**Input lead (from `sample_leads.csv`):**

| Field     | Value                                                                                                                                                                                |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Name      | James Harrington                                                                                                                                                                     |
| Company   | Deloitte                                                                                                                                                                             |
| Job Title | Head of Global Events                                                                                                                                                                |
| Message   | _"We are organising our annual leadership summit — 450 attendees, Bali, November 2025. Budget approved at $1.2M. We are finalising vendors this month and I am the decision-maker."_ |

**What gets sent to Groq:**

```
[system]  You are a senior SDR with 10+ years in the Tours, Travel, and
          Hospitality industry... [scoring criteria, score ranges, output format]

[user]    Name      : James Harrington
          Email     : j.harrington@deloitte-events.com
          Company   : Deloitte
          Job Title : Head of Global Events
          Message   : We are organising our annual leadership summit — 450
                      attendees, Bali, November 2025. Budget approved at $1.2M...
```

**What the LLM returns:**

```json
{
  "lead_score": 95,
  "industry": "Corporate Travel",
  "business_need": "Full-service destination management for a 450-person corporate leadership summit in Bali, including flights, accommodation, and event logistics.",
  "recommended_action": "Schedule a consultation call to discuss itinerary and pricing."
}
```

**What gets written to Google Sheets:**

| Name             | Company  | Job Title             | Score | Industry         | Business Need                                             | Recommended Action                                            | Processed At         |
| ---------------- | -------- | --------------------- | ----- | ---------------- | --------------------------------------------------------- | ------------------------------------------------------------- | -------------------- |
| James Harrington | Deloitte | Head of Global Events | 95    | Corporate Travel | Full-service DMC for 450-person leadership summit in Bali | Schedule a consultation call to discuss itinerary and pricing | 2025-01-15 10:32 UTC |

> All prompt templates live in [`src/prompts.py`](src/prompts.py). To change how the AI scores leads, edit only that file — no other code needs to change.

</details>

## Tech Stack

| Component        | Library / Service                            |
| ---------------- | -------------------------------------------- |
| Language         | Python 3.10+                                 |
| AI / LLM         | [Groq](https://groq.com) — `llama3-70b-8192` |
| Data validation  | Pydantic v2                                  |
| CSV processing   | pandas                                       |
| Google Sheets    | gspread + google-auth                        |
| Configuration    | python-dotenv                                |
| Progress display | tqdm                                         |
| Testing          | pytest                                       |

---

## Prerequisites

- Python 3.10 or higher
- A **Groq API key** (free tier available at [console.groq.com](https://console.groq.com))
- A **Google Cloud service account** with Sheets and Drive API access

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-lead-qualification.git
cd ai-lead-qualification
```

### 2. Create and activate a virtual environment (OPTIONAL)

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
# or
make install
```

### 4. Set up Google Cloud service account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Enable the **Google Sheets API** and **Google Drive API**.
4. Navigate to **IAM & Admin → Service Accounts** and create a new service account.
5. Grant the service account the **Editor** role.
6. Under **Keys**, create a new JSON key and download it.
7. Save the downloaded file as `credentials.json` in the project root.
8. Open the `credentials.json` file, copy the `client_email` value, and **share your Google Sheet with that email address** (Editor access).

### 5. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in values:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama3-70b-8192
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_NAME=Lead Qualification Results
```

### 6. Run Project

```bash
python -m src.main --input sample_leads.csv
# or
make run
```

---

## Example Output

**Terminal:**

```
2024-01-15 10:32:01 | INFO     | src.main — Loading leads from 'sample_leads.csv'...
2024-01-15 10:32:01 | INFO     | src.csv_reader — Loaded 25 valid lead(s) from 'sample_leads.csv'
2024-01-15 10:32:01 | INFO     | src.main — Initialising AI analyser and Google Sheets writer...
Qualifying leads: 100%|████████████████████| 25/25 [01:43<00:00,  4.1s/lead]

══════════════════════════════════════════════════════
  AI LEAD QUALIFICATION — RESULTS SUMMARY
══════════════════════════════════════════════════════
  Total processed  :  25
  Failed           :  0
  Average score    :  52.4 / 100
  ──────────────────────────────────────────────────
  High   (≥70)     :    8  ████████
  Medium (40–69)   :    9  █████████
  Low    (<40)     :    8  ████████
  ──────────────────────────────────────────────────
  Top leads:
    1. Sarah Johnson        (BrightTech) — Score: 91
    2. Robert Martinez      (ScaleForce) — Score: 89
    3. Jennifer Williams    (NovaPay) — Score: 87
══════════════════════════════════════════════════════
```

---

## Scoring Methodology

The LLM is instructed to follow these explicit scoring tiers:

| Score Range | Tier        | Criteria                                                                               |
| ----------- | ----------- | -------------------------------------------------------------------------------------- |
| 80 – 100    | High        | Decision-maker (C-Suite/VP/Director), explicit budget signal, specific and urgent need |
| 60 – 79     | Medium-High | Mid-level manager, genuine interest, some specificity, plausible authority             |
| 40 – 59     | Medium      | Individual contributor, exploratory intent, unclear authority                          |
| 20 – 39     | Low         | Personal inquiry, no budget signal, vague or unrelated context                         |
| 0 – 19      | Very Low    | Spam, student, job seeker, automated bot, no business relevance                        |

Scores are generated by the LLM based on four signal categories:

1. **Job title seniority** — VP/C-level outweigh managers; managers outweigh ICs
2. **Message specificity** — Specific pain points, timelines, or budgets score higher
3. **Company context** — Recognisable companies or specific industry context score higher
4. **Intent signals** — Words like "urgent", "budget approved", "decision-maker" boost score

---

## Project Structure

```
ai-lead-qualification/
├── README.md                  # This file
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
├── Makefile                   # Convenience commands
├── sample_leads.csv           # 25 realistic sample leads (high/medium/low mix)
│
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point — CLI + pipeline orchestration
│   ├── config.py              # Env var loading and startup validation
│   ├── models.py              # Pydantic models: Lead, LeadAnalysis, ProcessedLead
│   ├── csv_reader.py          # CSV loading and row validation (pandas)
│   ├── prompts.py             # LLM prompt templates and scoring guidelines
│   ├── lead_scorer.py         # Score categorisation logic and prompt assembly
│   ├── ai_analyzer.py         # Groq API calls, JSON parsing, retry logic
│   └── sheets_writer.py       # Google Sheets authentication and row writing
│
├── tests/
│   ├── __init__.py
│   └── test_models.py         # Pydantic model unit tests
│
└── Dashboard/
    ├── index.html             # Dashboard entry point — open in any browser
    ├── app.js                 # Data fetching, filtering, pagination, rendering
    ├── styles.css             # Dark theme styles
    ├── config.example.js      # Config template (committed)
    └── config.js              # Generated from .env — gitignored, never committed
```
