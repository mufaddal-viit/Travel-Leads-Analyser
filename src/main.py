"""
Main entry point for the AI Lead Qualification Automation pipeline.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import List, Tuple

from tqdm import tqdm

from src.ai_analyzer import AIAnalyzer
from src.config import validate_config
from src.csv_reader import CSVReader
from src.lead_scorer import categorize_score
from src.models import Lead, ProcessedLead
from src.sheets_writer import SheetsWriter

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── CLI argument parsing ───────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    """Define and parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="lead-qualifier",
        description=(
            "AI Lead Qualification Automation — reads leads from a CSV file, "
            "analyses each one with Groq AI, and writes the results to Google Sheets."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m src.main --input sample_leads.csv\n"
            "  python -m src.main --input leads.csv --log-level DEBUG\n"
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="FILE",
        help="Path to the input CSV file containing sales leads.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Logging verbosity (default: INFO). Options: DEBUG, INFO, WARNING, ERROR.",
    )
    return parser.parse_args()


# ── Pipeline ───────────────────────────────────────────────────────────────────

def run_pipeline(
    input_file: str,
) -> Tuple[List[ProcessedLead], List[Lead]]:
    """
    Execute the full lead qualification pipeline end-to-end.

    Steps:
        1. Load and validate leads from the CSV file.
        2. Initialise AI analyser and Sheets writer.
        3. For each lead: analyse with AI, build ProcessedLead, write to Sheets.
        4. Log failures without interrupting the rest of the batch.

    Args:
        input_file: Path to the CSV file containing raw leads.

    Returns:
        A tuple of (successfully processed leads, leads that failed).
    """
    # 1. Load leads
    logger.info("Loading leads from '%s'...", input_file)
    reader = CSVReader(input_file)
    leads = reader.load()

    if not leads:
        logger.warning("No valid leads found in '%s'. Exiting.", input_file)
        return [], []

    # 2. Initialise services
    logger.info("Initialising AI analyser and Google Sheets writer...")
    analyzer = AIAnalyzer()
    writer = SheetsWriter()

    processed_leads: List[ProcessedLead] = []
    failed_leads: List[Lead] = []

    # 3. Process each lead
    logger.info("Starting analysis of %d lead(s)...", len(leads))
    for lead in tqdm(leads, desc="Qualifying leads", unit="lead", ncols=72):
        try:
            analysis = analyzer.analyze_lead(lead)

            processed = ProcessedLead(
                **lead.model_dump(),
                **analysis.model_dump(),
                processed_at=datetime.now(timezone.utc),
            )

            writer.write_lead(processed)
            processed_leads.append(processed)

        except Exception as exc:
            logger.error(
                "Failed to process '%s' <%s>: %s",
                lead.name,
                lead.email,
                exc,
            )
            failed_leads.append(lead)

    return processed_leads, failed_leads


# ── Summary output ─────────────────────────────────────────────────────────────

def _print_summary(
    processed: List[ProcessedLead],
    failed: List[Lead],
) -> None:
    """Print a formatted summary table to stdout after the pipeline completes."""
    border = "═" * 54

    print(f"\n{border}")
    print("  AI LEAD QUALIFICATION — RESULTS SUMMARY")
    print(border)

    total = len(processed)

    if total == 0:
        print("  No leads were successfully processed.")
        if failed:
            print(f"  Failed : {len(failed)} lead(s)")
        print(f"{border}\n")
        return

    avg_score = sum(lead.lead_score for lead in processed) / total
    high   = [l for l in processed if l.lead_score >= 70]
    medium = [l for l in processed if 40 <= l.lead_score < 70]
    low    = [l for l in processed if l.lead_score < 40]

    print(f"  Total processed  :  {total}")
    print(f"  Failed           :  {len(failed)}")
    print(f"  Average score    :  {avg_score:.1f} / 100")
    print(f"  {'─' * 50}")
    print(f"  High   (≥70)     :  {len(high):>3}  " + "█" * min(len(high), 30))
    print(f"  Medium (40–69)   :  {len(medium):>3}  " + "█" * min(len(medium), 30))
    print(f"  Low    (<40)     :  {len(low):>3}  " + "█" * min(len(low), 30))

    if high:
        print(f"  {'─' * 50}")
        print("  Top leads:")
        top_three = sorted(processed, key=lambda x: x.lead_score, reverse=True)[:3]
        for rank, lead in enumerate(top_three, start=1):
            print(
                f"    {rank}. {lead.name:<22} "
                f"({lead.company_name}) — Score: {lead.lead_score}"
            )

    if failed:
        print(f"  {'─' * 50}")
        print("  Failed leads (check logs for details):")
        for lead in failed:
            print(f"    • {lead.name} <{lead.email}>")

    print(f"{border}\n")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Orchestrate the full pipeline: parse args → validate config → run → summarise."""
    args = _parse_args()

    # Apply requested log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Fail fast if configuration is incomplete
    try:
        validate_config()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    logger.info("AI Lead Qualification pipeline started.")

    try:
        processed, failed = run_pipeline(args.input)
        _print_summary(processed, failed)

        # Exit with non-zero code if nothing was processed, so CI/CD can detect failures
        if not processed:
            sys.exit(1)

    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
