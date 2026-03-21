"""
HTML email builder for the Job Alert system.
Produces a styled, responsive HTML email with:
  - Header (candidate name, date, summary stats)
  - Individual job cards with CTA buttons
  - Strengths / weaknesses section per job
  - Footer summary table with ATS / resume tips
"""

from __future__ import annotations
from datetime import datetime
import resume_profile as rp

# ── Colour palette ────────────────────────────────────────────────────────────
PRIMARY     = "#1a3c5e"   # deep navy
ACCENT      = "#0077b6"   # bright blue
SUCCESS     = "#2d6a4f"   # green (strengths)
WARNING     = "#b5451b"   # warm red (weaknesses)
GOLD        = "#e9c46a"   # header accent
BG_LIGHT    = "#f4f7fb"   # page background
CARD_BG     = "#ffffff"
BORDER      = "#dce3eb"
TEXT_DARK   = "#1f2937"
TEXT_MID    = "#4b5563"
TEXT_LIGHT  = "#6b7280"


def _cta_button(url: str, label: str = "View Job", bg: str = ACCENT) -> str:
    return (
        f'<a href="{url}" target="_blank" '
        f'style="display:inline-block;padding:11px 24px;background:{bg};'
        f'color:#ffffff;text-decoration:none;border-radius:6px;'
        f'font-family:Arial,sans-serif;font-size:14px;font-weight:600;'
        f'letter-spacing:0.3px;">&#128336; {label}</a>'
    )


def _badge(text: str, colour: str) -> str:
    return (
        f'<span style="display:inline-block;padding:3px 10px;'
        f'background:{colour}1a;color:{colour};border:1px solid {colour}55;'
        f'border-radius:12px;font-size:12px;font-weight:600;'
        f'margin:2px 3px 2px 0;">{text}</span>'
    )


def _score_bar(score: float) -> str:
    pct = round(score * 100)
    colour = SUCCESS if pct >= 85 else (ACCENT if pct >= 70 else WARNING)
    return (
        f'<div style="background:#e5e7eb;border-radius:999px;height:8px;'
        f'width:180px;display:inline-block;vertical-align:middle;">'
        f'<div style="background:{colour};width:{pct}%;height:8px;'
        f'border-radius:999px;"></div></div>'
        f'&nbsp;<strong style="color:{colour};font-size:13px;">{pct}%</strong>'
    )


def _job_card(job: dict, index: int) -> str:
    a = job.get("analysis", {})
    score      = job.get("display_score", job.get("match_score", 0))
    strengths  = a.get("strengths", [])
    weaknesses = a.get("weaknesses", [])
    reason     = a.get("relevance_reason", "")
    salary     = job.get("salary", "Not disclosed")
    emp_type   = job.get("employment_type", "")
    source     = job.get("source", "")
    posted     = job.get("posted_date", "")

    # Format posted date nicely
    posted_display = posted
    if posted and "T" in posted:
        try:
            posted_display = datetime.fromisoformat(
                posted.replace("Z", "+00:00")).strftime("%d %b %Y")
        except Exception:
            pass

    strengths_html = "".join(
        f'<li style="margin:4px 0;color:{TEXT_DARK};">'
        f'<span style="color:{SUCCESS};font-weight:700;">&#10003;</span> {s}</li>'
        for s in strengths
    )
    weaknesses_html = "".join(
        f'<li style="margin:4px 0;color:{TEXT_DARK};">'
        f'<span style="color:{WARNING};font-weight:700;">&#9888;</span> {s}</li>'
        for s in weaknesses
    )

    meta_parts = []
    if salary and salary != "Not disclosed":
        meta_parts.append(f"&#128181; {salary}")
    if emp_type:
        meta_parts.append(f"&#128188; {emp_type}")
    if posted_display:
        meta_parts.append(f"&#128197; {posted_display}")
    if source:
        meta_parts.append(f"&#127758; {source}")
    meta_html = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(meta_parts)

    return f"""
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="margin-bottom:24px;border-radius:10px;overflow:hidden;
              border:1px solid {BORDER};background:{CARD_BG};
              box-shadow:0 2px 8px rgba(0,0,0,0.06);">
  <!-- Card header -->
  <tr>
    <td style="background:linear-gradient(135deg,{PRIMARY},{ACCENT});
               padding:18px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <div style="color:#ffffff;font-size:10px;font-weight:600;
                        letter-spacing:1.5px;text-transform:uppercase;
                        margin-bottom:4px;">#{index} &nbsp;|&nbsp; {source}</div>
            <div style="color:#ffffff;font-size:20px;font-weight:700;
                        margin-bottom:2px;">{job['title']}</div>
            <div style="color:#b3d4f0;font-size:14px;">
              {job['company']} &nbsp;&#8226;&nbsp; {job['location']}
            </div>
          </td>
          <td style="text-align:right;vertical-align:top;white-space:nowrap;">
            <div style="background:rgba(255,255,255,0.15);border-radius:8px;
                        padding:8px 14px;display:inline-block;">
              <div style="color:#e0f0ff;font-size:10px;margin-bottom:3px;">
                MATCH SCORE</div>
              {_score_bar(score)}
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- Meta row -->
  <tr>
    <td style="background:#f0f6ff;padding:10px 24px;
               border-bottom:1px solid {BORDER};
               font-size:12px;color:{TEXT_MID};">
      {meta_html}
    </td>
  </tr>
  <!-- Body -->
  <tr>
    <td style="padding:20px 24px;">
      <!-- Why relevant -->
      {"<p style='margin:0 0 16px;font-size:13px;color:" + TEXT_MID + ";font-style:italic;'>" + reason + "</p>" if reason else ""}

      <!-- Strengths vs Weaknesses -->
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="50%" valign="top"
              style="padding-right:12px;border-right:1px solid {BORDER};">
            <div style="font-size:13px;font-weight:700;color:{SUCCESS};
                        margin-bottom:8px;text-transform:uppercase;
                        letter-spacing:0.5px;">&#128994; Strengths</div>
            <ul style="margin:0;padding-left:16px;font-size:13px;
                       line-height:1.7;list-style:none;">
              {strengths_html}
            </ul>
          </td>
          <td width="50%" valign="top" style="padding-left:12px;">
            <div style="font-size:13px;font-weight:700;color:{WARNING};
                        margin-bottom:8px;text-transform:uppercase;
                        letter-spacing:0.5px;">&#128308; Watch-outs</div>
            <ul style="margin:0;padding-left:16px;font-size:13px;
                       line-height:1.7;list-style:none;">
              {weaknesses_html}
            </ul>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <!-- CTA footer -->
  <tr>
    <td style="padding:16px 24px;background:#f8fafc;
               border-top:1px solid {BORDER};text-align:right;">
      {_cta_button(job['url'], "View Job Posting &#8594;")}
    </td>
  </tr>
</table>"""


def _summary_row(job: dict, index: int) -> str:
    a = job.get("analysis", {})
    tips = a.get("resume_tips", [])
    reason = a.get("relevance_reason", "—")
    score = round(job.get("display_score", job.get("match_score", 0)) * 100)
    tips_html = "<br>".join(f"• {t}" for t in tips) if tips else "—"
    row_bg = "#f9fafb" if index % 2 == 0 else "#ffffff"
    colour = SUCCESS if score >= 85 else (ACCENT if score >= 70 else WARNING)

    return f"""
<tr style="background:{row_bg};">
  <td style="padding:14px 16px;border-bottom:1px solid {BORDER};
             font-size:13px;font-weight:600;color:{TEXT_DARK};">
    {job['title']}<br>
    <span style="font-weight:400;color:{TEXT_MID};">{job['company']}</span><br>
    <span style="color:{colour};font-weight:700;font-size:12px;">{score}% match</span>
  </td>
  <td style="padding:14px 16px;border-bottom:1px solid {BORDER};
             font-size:12px;color:{TEXT_MID};line-height:1.6;">
    {reason}
  </td>
  <td style="padding:14px 16px;border-bottom:1px solid {BORDER};
             font-size:12px;color:{TEXT_MID};line-height:1.7;">
    {tips_html}
  </td>
  <td style="padding:14px 16px;border-bottom:1px solid {BORDER};text-align:center;">
    {_cta_button(job['url'], "Apply", bg=PRIMARY)}
  </td>
</tr>"""


def build_email(jobs: list[dict], role_category: str = "AP / Finance") -> tuple[str, str]:
    """
    Build the full HTML email.
    Returns (subject_line, html_body).

    role_category: label shown in the email header, e.g. "AP / Finance" or "Underwriting".
    """
    today = datetime.now().strftime("%d %B %Y")
    count = len(jobs)
    top_score = round(jobs[0]["match_score"] * 100) if jobs else 0

    subject = (
        f"&#127381; {count} {role_category} Job Alert{'s' if count != 1 else ''} for You "
        f"— {today}"
    )

    # ── Individual job cards ──────────────────────────────────────────────────
    cards_html = ""
    if jobs:
        for i, job in enumerate(jobs, 1):
            cards_html += _job_card(job, i)
    else:
        cards_html = (
            '<p style="text-align:center;color:#6b7280;padding:40px;">'
            'No new matching jobs found this cycle. Check back in 2 days!</p>'
        )

    # ── Summary table rows ────────────────────────────────────────────────────
    table_rows = "".join(_summary_row(j, i) for i, j in enumerate(jobs))

    # ── Sources breakdown ─────────────────────────────────────────────────────
    from collections import Counter
    source_counts = Counter(j.get("source", "Other") for j in jobs)
    source_badges = "".join(
        _badge(f"{src}: {cnt}", ACCENT) for src, cnt in source_counts.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Job Alert — {today}</title>
</head>
<body style="margin:0;padding:0;background:{BG_LIGHT};
             font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:{BG_LIGHT};">
<tr><td align="center" style="padding:32px 16px;">

  <!-- Outer container -->
  <table width="680" cellpadding="0" cellspacing="0" border="0"
         style="max-width:680px;width:100%;">

    <!-- ── HEADER ──────────────────────────────────────────────────────── -->
    <tr>
      <td style="background:linear-gradient(135deg,{PRIMARY} 0%,#0d2b4e 100%);
                 border-radius:12px 12px 0 0;padding:36px 36px 28px;">
        <div style="color:{GOLD};font-size:11px;font-weight:700;
                    letter-spacing:2px;text-transform:uppercase;
                    margin-bottom:8px;">Personalised Job Alert — {role_category}</div>
        <div style="color:#ffffff;font-size:26px;font-weight:700;
                    margin-bottom:4px;">Hi, {rp.CANDIDATE_NAME.split()[0]}! 👋</div>
        <div style="color:#b3d4f0;font-size:14px;margin-bottom:20px;">
          Here are your curated job matches for <strong
          style="color:#ffffff;">{today}</strong>
        </div>
        <!-- Stats row -->
        <table cellpadding="0" cellspacing="0">
          <tr>
            <td style="background:rgba(255,255,255,0.12);border-radius:8px;
                       padding:12px 20px;margin-right:12px;text-align:center;">
              <div style="color:{GOLD};font-size:28px;font-weight:700;">{count}</div>
              <div style="color:#b3d4f0;font-size:11px;">Matched Jobs</div>
            </td>
            <td width="12"></td>
            <td style="background:rgba(255,255,255,0.12);border-radius:8px;
                       padding:12px 20px;text-align:center;">
              <div style="color:{GOLD};font-size:28px;font-weight:700;">{top_score}%</div>
              <div style="color:#b3d4f0;font-size:11px;">Top Match</div>
            </td>
            <td width="12"></td>
            <td style="background:rgba(255,255,255,0.12);border-radius:8px;
                       padding:12px 20px;text-align:center;">
              <div style="color:{GOLD};font-size:28px;font-weight:700;">14d</div>
              <div style="color:#b3d4f0;font-size:11px;">Freshness Filter</div>
            </td>
          </tr>
        </table>
      </td>
    </tr>

    <!-- ── SOURCES BAR ──────────────────────────────────────────────────── -->
    <tr>
      <td style="background:#e8f0fe;padding:12px 36px;
                 border:1px solid {BORDER};border-top:none;">
        <span style="font-size:12px;color:{TEXT_MID};margin-right:8px;">
          Sources:
        </span>
        {source_badges}
        <span style="font-size:12px;color:{TEXT_LIGHT};float:right;">
          &#127462;&#127468; Singapore only &nbsp;&#10003;
        </span>
      </td>
    </tr>

    <!-- ── MAIN CONTENT (individual job cards) ────────────────────────────── -->
    <tr>
      <td style="background:{CARD_BG};padding:28px 36px;
                 border:1px solid {BORDER};border-top:none;">

        <h2 style="margin:0 0 20px;font-size:16px;color:{PRIMARY};
                   border-bottom:2px solid {ACCENT};padding-bottom:10px;">
          &#127775; Top Matched Roles
        </h2>

        {cards_html}

      </td>
    </tr>

    <!-- ── SUMMARY TABLE ───────────────────────────────────────────────── -->
    <tr>
      <td style="background:{CARD_BG};padding:28px 36px 28px;
                 border:1px solid {BORDER};border-top:none;">
        <h2 style="margin:0 0 16px;font-size:16px;color:{PRIMARY};
                   border-bottom:2px solid {ACCENT};padding-bottom:10px;">
          &#128203; Summary &amp; Resume Optimisation Tips
        </h2>
        <table width="100%" cellpadding="0" cellspacing="0"
               style="border:1px solid {BORDER};border-radius:8px;
                      overflow:hidden;font-size:13px;">
          <tr style="background:{PRIMARY};">
            <th style="padding:12px 16px;color:#ffffff;text-align:left;
                       font-weight:600;font-size:12px;width:22%;">Role / Company</th>
            <th style="padding:12px 16px;color:#ffffff;text-align:left;
                       font-weight:600;font-size:12px;width:28%;">Why It Fits</th>
            <th style="padding:12px 16px;color:#ffffff;text-align:left;
                       font-weight:600;font-size:12px;width:38%;">Resume &amp; ATS Tips</th>
            <th style="padding:12px 16px;color:#ffffff;text-align:center;
                       font-weight:600;font-size:12px;width:12%;">Link</th>
          </tr>
          {table_rows if table_rows else
           '<tr><td colspan="4" style="padding:20px;text-align:center;color:#6b7280;">'
           'No jobs to display.</td></tr>'}
        </table>
      </td>
    </tr>

    <!-- ── FOOTER ──────────────────────────────────────────────────────── -->
    <tr>
      <td style="background:{PRIMARY};border-radius:0 0 12px 12px;
                 padding:24px 36px;text-align:center;">
        <div style="color:#b3d4f0;font-size:12px;line-height:1.8;">
          This alert was generated automatically from
          <strong style="color:#ffffff;">MyCareersFuture</strong>,
          <strong style="color:#ffffff;">Indeed</strong>,
          <strong style="color:#ffffff;">JobStreet</strong>, and
          <strong style="color:#ffffff;">LinkedIn</strong>.<br>
          Showing Singapore roles posted in the last 14 days with ≥70% profile match
          &amp; min SGD 4,000 salary.<br>
          <span style="color:{GOLD};">Next alert in 2 days.</span>
        </div>
        <div style="margin-top:12px;color:#6b87a0;font-size:11px;">
          Sent to {rp.CANDIDATE_EMAIL} &nbsp;|&nbsp; {today}
        </div>
      </td>
    </tr>

  </table>
</td></tr>
</table>

</body>
</html>"""

    return subject, html
