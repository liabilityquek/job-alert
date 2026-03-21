"""
sheets_tracker.py

Handles dedup tracking AND job logging via Google Sheets (Composio).
Google Sheets is the single source of truth — no local sent_jobs.json needed.
"""

import os
from datetime import datetime


# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

def _get_toolset():
    """Return a Composio ToolSet instance."""
    from composio import ComposioToolSet  # type: ignore
    return ComposioToolSet()


def _get_sheet_id() -> str | None:
    """Return the tracker sheet ID from env, or None."""
    return os.environ.get("TRACKER_SHEET_ID")


def _read_sent_urls_from_sheet(sheet_id: str) -> set:
    """Read all job URLs (column C) from the Google Sheet."""
    try:
        from composio import Action  # type: ignore
        toolset = _get_toolset()

        result = toolset.execute_action(
            action=Action.GOOGLESHEETS_BATCH_GET,
            params={
                "spreadsheet_id": sheet_id,
                "sheet_name": "Sheet1",
                "ranges": "Sheet1!C:C",
            },
        )

        urls = set()
        if result.get("successfull") or result.get("successful"):
            data = result.get("data", {})
            value_ranges = data.get("valueRanges", [])
            if value_ranges:
                rows = value_ranges[0].get("values", [])
                for row in rows[1:]:  # skip header row
                    if row and row[0]:
                        urls.add(row[0].strip())

        print(f"[sheets_tracker] Read {len(urls)} existing URL(s) from Google Sheet.")
        return urls

    except Exception as exc:
        print(f"[sheets_tracker] Error reading from Google Sheet: {exc}")
        return set()


# ---------------------------------------------------------------------------
# Dedup — reads from Google Sheets
# ---------------------------------------------------------------------------

def filter_new_jobs(jobs: list, pipeline: str) -> list:
    """Remove jobs whose URL already exists in the Google Sheet.

    Each job is expected to be a dict with at least a ``url`` key.
    Falls back to no filtering if Google Sheets is unavailable.
    """
    sheet_id = _get_sheet_id()
    if not sheet_id:
        print("[sheets_tracker] TRACKER_SHEET_ID not set — skipping dedup.")
        return jobs

    sent_urls = _read_sent_urls_from_sheet(sheet_id)
    if not sent_urls:
        return jobs

    new_jobs = [j for j in jobs if j.get("url") not in sent_urls]
    skipped = len(jobs) - len(new_jobs)
    if skipped:
        print(f"[sheets_tracker] Filtered out {skipped} already-sent job(s) "
              f"for pipeline '{pipeline}'.")
    return new_jobs


# ---------------------------------------------------------------------------
# Log to Google Sheets (append new rows)
# ---------------------------------------------------------------------------

def log_to_sheet(jobs: list, pipeline: str) -> None:
    """Append matched jobs to the Google Sheet via Composio.

    Requires ``TRACKER_SHEET_ID`` env var set to the target spreadsheet ID.
    Fails gracefully if not configured.
    """
    sheet_id = _get_sheet_id()
    if not sheet_id:
        print("[sheets_tracker] TRACKER_SHEET_ID not set — skipping "
              "Google Sheets logging.")
        return

    if not jobs:
        return

    try:
        from composio import Action  # type: ignore
        toolset = _get_toolset()
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
                "New",  # default status for tracking
            ])

        toolset.execute_action(
            action=Action.GOOGLESHEETS_BATCH_UPDATE,
            params={
                "spreadsheet_id": sheet_id,
                "sheet_name": "Sheet1",
                "range": "A:H",
                "values": rows,
                "major_dimension": "ROWS",
            },
        )
        print(f"[sheets_tracker] Logged {len(rows)} job(s) to Google Sheet "
              f"for pipeline '{pipeline}'.")

    except Exception as exc:
        print(f"[sheets_tracker] Failed to log to Google Sheet: {exc}")


# ---------------------------------------------------------------------------
# mark_jobs_sent — now a no-op (Google Sheets handles everything)
# ---------------------------------------------------------------------------

def mark_jobs_sent(jobs: list, pipeline: str) -> None:
    """No-op — dedup and logging are handled entirely via Google Sheets."""
    pass
