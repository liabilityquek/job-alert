"""
sheets_tracker.py

Handles dedup tracking via sent_jobs.json and optional Google Sheets
dashboard logging via Composio.
"""

import os
import json
from pathlib import Path
from datetime import datetime

SENT_JOBS_PATH = Path(__file__).parent / "sent_jobs.json"


# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------

def load_sent_urls() -> set:
    """Return a set of URLs that have already been sent."""
    data = _load_sent_data()
    return set(data.keys())


def save_sent_urls(data: dict) -> None:
    """Write the full sent-jobs dict to sent_jobs.json."""
    try:
        with open(SENT_JOBS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except OSError as exc:
        print(f"[sheets_tracker] Error writing {SENT_JOBS_PATH}: {exc}")


def filter_new_jobs(jobs: list, pipeline: str) -> list:
    """Remove jobs whose URL already appears in sent_jobs.json.

    Each job is expected to be a dict with at least a ``url`` key.
    """
    sent_urls = load_sent_urls()
    new_jobs = [j for j in jobs if j.get("url") not in sent_urls]
    skipped = len(jobs) - len(new_jobs)
    if skipped:
        print(f"[sheets_tracker] Filtered out {skipped} already-sent job(s) "
              f"for pipeline '{pipeline}'.")
    return new_jobs


def mark_jobs_sent(jobs: list, pipeline: str) -> None:
    """Record jobs in sent_jobs.json after a successful email send.

    Each job dict should contain ``url``, ``title``, ``company``,
    ``source``, and ``score`` keys.
    """
    if not jobs:
        return

    data = _load_sent_data()
    now = datetime.now().isoformat()

    for job in jobs:
        url = job.get("url")
        if not url:
            continue
        data[url] = {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "source": job.get("source", ""),
            "score": job.get("score", 0),
            "date_found": now,
            "pipeline": pipeline,
        }

    save_sent_urls(data)
    print(f"[sheets_tracker] Marked {len(jobs)} job(s) as sent "
          f"for pipeline '{pipeline}'.")


# ---------------------------------------------------------------------------
# Google Sheets dashboard (Composio)
# ---------------------------------------------------------------------------

def log_to_sheet(jobs: list, pipeline: str) -> None:
    """Append matched jobs to a Google Sheet via Composio.

    Requires:
      - ``TRACKER_SHEET_ID`` env var set to the target spreadsheet ID.
      - The ``composio_openai`` package installed and configured.

    Fails gracefully if either requirement is not met.
    """
    sheet_id = os.environ.get("TRACKER_SHEET_ID")
    if not sheet_id:
        print("[sheets_tracker] TRACKER_SHEET_ID not set — skipping "
              "Google Sheets logging.")
        return

    if not jobs:
        return

    try:
        from composio import ComposioToolSet, Action  # type: ignore
    except ImportError:
        print("[sheets_tracker] composio package not installed — skipping "
              "Google Sheets logging.")
        return

    try:
        toolset = ComposioToolSet()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        rows = []
        for job in jobs:
            rows.append([
                job.get("title", ""),
                job.get("company", ""),
                job.get("url", ""),
                job.get("source", ""),
                str(job.get("score", "")),
                pipeline,
                now,
            ])

        toolset.execute_action(
            action=Action.GOOGLESHEETS_BATCH_UPDATE,
            params={
                "spreadsheet_id": sheet_id,
                "range": "Sheet1!A:G",
                "values": rows,
                "major_dimension": "ROWS",
            },
        )
        print(f"[sheets_tracker] Logged {len(rows)} job(s) to Google Sheet "
              f"for pipeline '{pipeline}'.")

    except Exception as exc:
        print(f"[sheets_tracker] Failed to log to Google Sheet: {exc}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_sent_data() -> dict:
    """Load and return the sent-jobs dict from disk."""
    if not SENT_JOBS_PATH.exists():
        return {}
    try:
        with open(SENT_JOBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[sheets_tracker] Error reading {SENT_JOBS_PATH}: {exc}")
        return {}
