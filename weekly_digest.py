"""
weekly_digest.py

Generates and sends a weekly job market summary digest email.
Reads sent_jobs.json to compute stats for the past 7 days and sends
a styled HTML dashboard via Composio Gmail.
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

from dotenv import load_dotenv

import email_sender
from email_builder import (
    PRIMARY, ACCENT, GOLD, SUCCESS, WARNING,
    BG_LIGHT, CARD_BG, BORDER, TEXT_DARK, TEXT_MID, TEXT_LIGHT,
)

load_dotenv()

SENT_JOBS_PATH = Path(__file__).parent / "sent_jobs.json"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_sent_data() -> dict:
    """Load the full sent_jobs.json dict from disk."""
    if not SENT_JOBS_PATH.exists():
        return {}
    try:
        with open(SENT_JOBS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[weekly_digest] Error reading {SENT_JOBS_PATH}: {exc}")
        return {}


def _jobs_last_7_days(data: dict) -> list[dict]:
    """Return entries from sent_jobs.json whose date_found is within the past 7 days."""
    cutoff = datetime.now() - timedelta(days=7)
    recent = []
    for url, info in data.items():
        date_str = info.get("date_found", "")
        if not date_str:
            continue
        try:
            found_dt = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            continue
        if found_dt >= cutoff:
            entry = dict(info)
            entry["url"] = url
            recent.append(entry)
    return recent


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def _compute_stats(jobs: list[dict]) -> dict:
    """Compute digest statistics from a list of job entries."""
    pipelines: dict[str, list[dict]] = {}
    sources: Counter = Counter()
    companies: Counter = Counter()
    scores: list[float] = []

    for job in jobs:
        pipeline = job.get("pipeline", "Other")
        pipelines.setdefault(pipeline, []).append(job)

        source = job.get("source", "Unknown")
        sources[source] += 1

        company = job.get("company", "Unknown")
        if company:
            companies[company] += 1

        score = job.get("score", 0)
        if isinstance(score, (int, float)) and score > 0:
            scores.append(float(score))

    avg_score = sum(scores) / len(scores) if scores else 0.0
    top_companies = companies.most_common(5)
    top_sources = sources.most_common(10)

    return {
        "total": len(jobs),
        "pipelines": pipelines,
        "avg_score": avg_score,
        "top_companies": top_companies,
        "top_sources": top_sources,
    }


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _build_no_activity_email() -> tuple[str, str]:
    """Return (subject, html) for a week with no job activity."""
    today = datetime.now().strftime("%d %B %Y")
    subject = f"Weekly Job Market Digest — No Activity ({today})"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:{BG_LIGHT};font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BG_LIGHT};">
<tr><td align="center" style="padding:32px 16px;">
  <table width="680" cellpadding="0" cellspacing="0" border="0" style="max-width:680px;width:100%;">
    <tr>
      <td style="background:linear-gradient(135deg,{PRIMARY} 0%,#0d2b4e 100%);
                 border-radius:12px 12px 0 0;padding:36px;text-align:center;">
        <div style="color:{GOLD};font-size:11px;font-weight:700;letter-spacing:2px;
                    text-transform:uppercase;margin-bottom:8px;">Weekly Digest</div>
        <div style="color:#ffffff;font-size:24px;font-weight:700;">No Job Activity This Week</div>
        <div style="color:#b3d4f0;font-size:14px;margin-top:8px;">
          No new jobs were tracked during the past 7 days.
        </div>
      </td>
    </tr>
    <tr>
      <td style="background:{CARD_BG};padding:32px 36px;border:1px solid {BORDER};
                 border-top:none;text-align:center;">
        <p style="color:{TEXT_MID};font-size:14px;line-height:1.7;margin:0;">
          The job alert system did not find new matching roles this week.
          This could mean the market is quiet or the scrapers did not run.
          Check back next Sunday for an updated digest.
        </p>
      </td>
    </tr>
    <tr>
      <td style="background:{PRIMARY};border-radius:0 0 12px 12px;
                 padding:20px 36px;text-align:center;">
        <div style="color:#b3d4f0;font-size:12px;">
          Automated Weekly Digest &nbsp;|&nbsp; {today}
        </div>
      </td>
    </tr>
  </table>
</td></tr>
</table>
</body></html>"""
    return subject, html


def _pipeline_stat_cell(name: str, jobs: list[dict]) -> str:
    """Build one pipeline stats column cell."""
    count = len(jobs)
    scores = [float(j.get("score", 0)) for j in jobs if j.get("score")]
    avg = round((sum(scores) / len(scores)) * 100) if scores else 0
    top = round(max(scores) * 100) if scores else 0

    return f"""
    <td width="50%" valign="top" style="padding:16px 20px;">
      <div style="font-size:13px;font-weight:700;color:{ACCENT};
                  text-transform:uppercase;letter-spacing:0.5px;
                  margin-bottom:12px;border-bottom:2px solid {ACCENT};
                  padding-bottom:8px;">{name}</div>
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td style="padding:6px 0;font-size:13px;color:{TEXT_MID};">New jobs found</td>
          <td style="padding:6px 0;font-size:16px;font-weight:700;color:{TEXT_DARK};
                     text-align:right;">{count}</td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:13px;color:{TEXT_MID};">Avg match score</td>
          <td style="padding:6px 0;font-size:16px;font-weight:700;color:{ACCENT};
                     text-align:right;">{avg}%</td>
        </tr>
        <tr>
          <td style="padding:6px 0;font-size:13px;color:{TEXT_MID};">Top match score</td>
          <td style="padding:6px 0;font-size:16px;font-weight:700;color:{SUCCESS};
                     text-align:right;">{top}%</td>
        </tr>
      </table>
    </td>"""


def _build_digest_email(stats: dict) -> tuple[str, str]:
    """Return (subject, html) for the full weekly digest."""
    today = datetime.now()
    week_start = (today - timedelta(days=7)).strftime("%d %b")
    week_end = today.strftime("%d %b %Y")
    date_range = f"{week_start} — {week_end}"

    subject = f"Weekly Job Market Digest — {date_range}"

    # Pipeline columns
    pipeline_names = list(stats["pipelines"].keys())
    # Ensure we always have two columns even if one pipeline is missing
    col1_name = pipeline_names[0] if len(pipeline_names) > 0 else "AP/Finance"
    col1_jobs = stats["pipelines"].get(col1_name, [])
    col2_name = pipeline_names[1] if len(pipeline_names) > 1 else "Underwriting"
    col2_jobs = stats["pipelines"].get(col2_name, [])

    # Top companies table rows
    companies_rows = ""
    for rank, (company, count) in enumerate(stats["top_companies"], 1):
        row_bg = "#f9fafb" if rank % 2 == 0 else "#ffffff"
        companies_rows += f"""
        <tr style="background:{row_bg};">
          <td style="padding:10px 16px;border-bottom:1px solid {BORDER};
                     font-size:13px;color:{TEXT_MID};text-align:center;">{rank}</td>
          <td style="padding:10px 16px;border-bottom:1px solid {BORDER};
                     font-size:13px;font-weight:600;color:{TEXT_DARK};">{company}</td>
          <td style="padding:10px 16px;border-bottom:1px solid {BORDER};
                     font-size:13px;color:{TEXT_DARK};text-align:center;">{count}</td>
        </tr>"""

    if not companies_rows:
        companies_rows = f"""
        <tr>
          <td colspan="3" style="padding:16px;text-align:center;color:{TEXT_LIGHT};
                                 font-size:13px;">No company data available.</td>
        </tr>"""

    # Sources badges
    source_badges = ""
    for src, cnt in stats["top_sources"]:
        source_badges += (
            f'<span style="display:inline-block;padding:5px 14px;'
            f'background:{ACCENT}1a;color:{ACCENT};border:1px solid {ACCENT}55;'
            f'border-radius:16px;font-size:12px;font-weight:600;'
            f'margin:3px 4px;">{src}: {cnt}</span>'
        )

    avg_pct = round(stats["avg_score"] * 100)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Weekly Job Market Digest — {date_range}</title>
</head>
<body style="margin:0;padding:0;background:{BG_LIGHT};
             font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:{BG_LIGHT};">
<tr><td align="center" style="padding:32px 16px;">

  <table width="680" cellpadding="0" cellspacing="0" border="0"
         style="max-width:680px;width:100%;">

    <!-- HEADER -->
    <tr>
      <td style="background:linear-gradient(135deg,{PRIMARY} 0%,#0d2b4e 100%);
                 border-radius:12px 12px 0 0;padding:36px 36px 28px;">
        <div style="color:{GOLD};font-size:11px;font-weight:700;
                    letter-spacing:2px;text-transform:uppercase;
                    margin-bottom:8px;">Weekly Digest</div>
        <div style="color:#ffffff;font-size:24px;font-weight:700;
                    margin-bottom:4px;">Weekly Job Market Digest</div>
        <div style="color:#b3d4f0;font-size:14px;margin-bottom:20px;">
          {date_range}
        </div>
        <!-- Stats row -->
        <table cellpadding="0" cellspacing="0">
          <tr>
            <td style="background:rgba(255,255,255,0.12);border-radius:8px;
                       padding:12px 20px;text-align:center;">
              <div style="color:{GOLD};font-size:28px;font-weight:700;">{stats['total']}</div>
              <div style="color:#b3d4f0;font-size:11px;">Total Jobs</div>
            </td>
            <td width="12"></td>
            <td style="background:rgba(255,255,255,0.12);border-radius:8px;
                       padding:12px 20px;text-align:center;">
              <div style="color:{GOLD};font-size:28px;font-weight:700;">{avg_pct}%</div>
              <div style="color:#b3d4f0;font-size:11px;">Avg Match</div>
            </td>
            <td width="12"></td>
            <td style="background:rgba(255,255,255,0.12);border-radius:8px;
                       padding:12px 20px;text-align:center;">
              <div style="color:{GOLD};font-size:28px;font-weight:700;">{len(stats['top_sources'])}</div>
              <div style="color:#b3d4f0;font-size:11px;">Sources</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- PIPELINE STATS — TWO COLUMNS -->
    <tr>
      <td style="background:{CARD_BG};padding:24px 16px;
                 border:1px solid {BORDER};border-top:none;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            {_pipeline_stat_cell(col1_name, col1_jobs)}
            <td width="1" style="background:{BORDER};"></td>
            {_pipeline_stat_cell(col2_name, col2_jobs)}
          </tr>
        </table>
      </td>
    </tr>

    <!-- TOP COMPANIES TABLE -->
    <tr>
      <td style="background:{CARD_BG};padding:24px 36px;
                 border:1px solid {BORDER};border-top:none;">
        <h2 style="margin:0 0 16px;font-size:16px;color:{PRIMARY};
                   border-bottom:2px solid {ACCENT};padding-bottom:10px;">
          Top 5 Companies by Listings
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border:1px solid {BORDER};border-radius:8px;overflow:hidden;">
          <tr style="background:{PRIMARY};">
            <th style="padding:10px 16px;color:#ffffff;text-align:center;
                       font-weight:600;font-size:12px;width:10%;">#</th>
            <th style="padding:10px 16px;color:#ffffff;text-align:left;
                       font-weight:600;font-size:12px;width:65%;">Company</th>
            <th style="padding:10px 16px;color:#ffffff;text-align:center;
                       font-weight:600;font-size:12px;width:25%;">Listings</th>
          </tr>
          {companies_rows}
        </table>
      </td>
    </tr>

    <!-- SOURCES -->
    <tr>
      <td style="background:{CARD_BG};padding:20px 36px;
                 border:1px solid {BORDER};border-top:none;">
        <h2 style="margin:0 0 12px;font-size:16px;color:{PRIMARY};
                   border-bottom:2px solid {ACCENT};padding-bottom:10px;">
          Job Sources
        </h2>
        <div style="text-align:center;">
          {source_badges}
        </div>
      </td>
    </tr>

    <!-- TIP / REMINDER -->
    <tr>
      <td style="background:#fffbeb;padding:20px 36px;
                 border:1px solid {BORDER};border-top:none;">
        <table cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td width="40" valign="top" style="padding-right:12px;">
              <div style="font-size:24px;">&#128161;</div>
            </td>
            <td>
              <div style="font-size:14px;font-weight:700;color:{PRIMARY};
                          margin-bottom:4px;">Weekly Reminder</div>
              <div style="font-size:13px;color:{TEXT_MID};line-height:1.6;">
                Remember to update your application status in the tracker.
                Keeping track of where you've applied helps avoid duplicate
                applications and lets you follow up at the right time.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td style="background:{PRIMARY};border-radius:0 0 12px 12px;
                 padding:24px 36px;text-align:center;">
        <div style="color:#b3d4f0;font-size:12px;line-height:1.8;">
          This digest summarises job activity from
          <strong style="color:#ffffff;">{date_range}</strong>.<br>
          Data sourced from <strong style="color:#ffffff;">MyCareersFuture</strong>,
          <strong style="color:#ffffff;">LinkedIn</strong>,
          <strong style="color:#ffffff;">Indeed</strong>, and
          <strong style="color:#ffffff;">JobStreet</strong>.<br>
          <span style="color:{GOLD};">Next digest: next Sunday at 10:00 AM SGT.</span>
        </div>
        <div style="margin-top:12px;color:#6b87a0;font-size:11px;">
          Automated Weekly Digest &nbsp;|&nbsp; {week_end}
        </div>
      </td>
    </tr>

  </table>
</td></tr>
</table>

</body></html>"""

    return subject, html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("[weekly_digest] Starting weekly digest generation...")

    data = _load_sent_data()
    if not data:
        print("[weekly_digest] sent_jobs.json not found or empty — sending no-activity email.")
        subject, html = _build_no_activity_email()
        email_sender.send_job_alert(subject, html)
        return

    recent_jobs = _jobs_last_7_days(data)
    if not recent_jobs:
        print("[weekly_digest] No jobs found in the past 7 days — sending no-activity email.")
        subject, html = _build_no_activity_email()
        email_sender.send_job_alert(subject, html)
        return

    print(f"[weekly_digest] Found {len(recent_jobs)} job(s) from the past 7 days.")
    stats = _compute_stats(recent_jobs)
    subject, html = _build_digest_email(stats)

    success = email_sender.send_job_alert(subject, html)
    if success:
        print("[weekly_digest] Weekly digest email sent successfully.")
    else:
        print("[weekly_digest] Failed to send weekly digest email.")


if __name__ == "__main__":
    main()
