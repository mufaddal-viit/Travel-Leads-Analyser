# AI Lead Qualification Automation

A Python automation system that reads inbound sales leads from a CSV file, analyses each one with a Groq-hosted LLM, assigns a lead score and qualification, then writes all results to Google Sheets — fully automated, end-to-end.

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

## Tech Stack

| Component             | Library / Service               |
|-----------------------|---------------------------------|
| Language              | Python 3.10+                    |
| AI / LLM              | [Groq](https://groq.com) — `llama3-70b-8192` |
| Data validation       | Pydantic v2                     |
| CSV processing        | pandas                          |
| Google Sheets         | gspread + google-auth           |
| Configuration         | python-dotenv                   |
| Progress display      | tqdm                            |
| Testing               | pytest                          |

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

### 2. Create and activate a virtual environment

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

Open `.env` and fill in your values:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama3-70b-8192
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_NAME=Lead Qualification Results
```

### 6. Run the pipeline

```bash
python -m src.main --input sample_leads.csv
# or
make run
```

For verbose output:

```bash
python -m src.main --input sample_leads.csv --log-level DEBUG
# or
make run-debug
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

**Google Sheet result (sample row):**

| Name | Email | Company | Job Title | Message | Lead Score | Industry | Business Need | Recommended Action | Processed At |
|------|-------|---------|-----------|---------|------------|----------|---------------|--------------------|--------------|
| Sarah Johnson | sarah.johnson@brighttech.io | BrightTech | VP of Sales | We're scaling our sales team... | 91 | SaaS | Scaling sales team requires CRM automation and AI-powered lead routing. | Schedule demo call with senior sales rep | 2024-01-15 10:32:05 UTC |

---

## Scoring Methodology

The LLM is instructed to follow these explicit scoring tiers:

| Score Range | Tier   | Criteria |
|-------------|--------|----------|
| 80 – 100    | High   | Decision-maker (C-Suite/VP/Director), explicit budget signal, specific and urgent need |
| 60 – 79     | Medium-High | Mid-level manager, genuine interest, some specificity, plausible authority |
| 40 – 59     | Medium | Individual contributor, exploratory intent, unclear authority |
| 20 – 39     | Low    | Personal inquiry, no budget signal, vague or unrelated context |
| 0 – 19      | Very Low | Spam, student, job seeker, automated bot, no business relevance |

Scores are generated by the LLM based on four signal categories:
1. **Job title seniority** — VP/C-level outweigh managers; managers outweigh ICs
2. **Message specificity** — Specific pain points, timelines, or budgets score higher
3. **Company context** — Recognisable companies or specific industry context score higher
4. **Intent signals** — Words like "urgent", "budget approved", "decision-maker" boost score

---

## Google Sheets Conditional Formatting (Manual Step)

After running the pipeline, apply colour coding in Google Sheets for visual scanning:

1. Select the **Lead Score** column (column F).
2. Go to **Format → Conditional formatting**.
3. Add three rules:
   - Score ≥ 70 → Background: **Green** (`#b7e1cd`)
   - Score ≥ 40 (and < 70) → Background: **Yellow** (`#fff2cc`)
   - Score < 40 → Background: **Red** (`#f4cccc`)

---

## Running Tests

```bash
python -m pytest tests/ -v
# or
make test
```

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
│   ├── lead_scorer.py         # Prompt template and score categorisation logic
│   ├── ai_analyzer.py         # Groq API calls, JSON parsing, retry logic
│   └── sheets_writer.py       # Google Sheets authentication and row writing
│
└── tests/
    ├── __init__.py
    └── test_models.py         # Pydantic model unit tests
```
