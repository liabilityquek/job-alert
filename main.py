"""
Job Alert System — Main Orchestrator
=====================================
Run this file directly to trigger one full cycle:
  python main.py

Or with flags:
  python main.py --test-email    # verify SMTP config only
  python main.py --dry-run       # scrape + match but don't send email
  python main.py --mcf-only      # scrape MyCareersFuture only (fastest)
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# ── Load environment variables ─────────────────────────────────────────────
# load_dotenv is a no-op when .env doesn't exist (e.g. on GitHub Actions)
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH, override=False)  # env vars set by CI take priority

# ── Validate .env before importing anything else ───────────────────────────
def _check_env() -> list[str]:
    warnings = []
    if not os.getenv("COMPOSIO_API_KEY"):
        warnings.append("COMPOSIO_API_KEY not set — email sending via Composio will fail.")
    if not os.getenv("EMAIL_RECIPIENTS"):
        warnings.append("EMAIL_RECIPIENTS not set — no recipients configured.")
    return warnings

# ── Imports (after env loaded) ─────────────────────────────────────────────
from scrapers import mycareersfuture, indeed, jobstreet
from matcher import match_and_analyse
from email_builder import build_email
from email_sender import send_job_alert, send_test_email


def run(dry_run: bool = False, mcf_only: bool = False) -> int:
    """
    Full pipeline:
      1. Scrape job portals
      2. Deduplicate
      3. Match against resume (>=70%)
      4. AI-enhance analysis
      5. Build HTML email
      6. Send email

    Returns the number of matched jobs.
    """
    print("=" * 60)
    print("  Job Alert System — Starting Run")
    print("=" * 60)

    # ── Step 1: Scrape ──────────────────────────────────────────────────────
    all_jobs: list[dict] = []

    print("\n[Step 1/4] Scraping job portals...")
    print("-" * 40)

    # MyCareersFuture (official Singapore API — most reliable)
    try:
        mcf_jobs = mycareersfuture.scrape()
        all_jobs.extend(mcf_jobs)
    except Exception as e:
        print(f"[Main] MyCareersFuture scraper error: {e}")

    if not mcf_only:
        # Indeed Singapore
        try:
            indeed_jobs = indeed.scrape()
            all_jobs.extend(indeed_jobs)
        except Exception as e:
            print(f"[Main] Indeed scraper error: {e}")

        # JobStreet Singapore
        try:
            js_jobs = jobstreet.scrape()
            all_jobs.extend(js_jobs)
        except Exception as e:
            print(f"[Main] JobStreet scraper error: {e}")

    # ── Deduplicate by URL ──────────────────────────────────────────────────
    seen_urls: set[str] = set()
    unique_jobs: list[dict] = []
    for job in all_jobs:
        url = job.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url:
            # Deduplicate by title+company if no URL
            key = f"{job['title']}|{job['company']}".lower()
            if key not in seen_urls:
                seen_urls.add(key)
                unique_jobs.append(job)

    print(f"\n[Main] Total scraped (deduplicated): {len(unique_jobs)} jobs")

    # ── Step 2: Match ───────────────────────────────────────────────────────
    print("\n[Step 2/4] Matching jobs against resume profile...")
    print("-" * 40)
    matched_jobs = match_and_analyse(unique_jobs)

    if not matched_jobs:
        print("[Main] No jobs met the 70% match threshold this cycle.")
        if not dry_run:
            # Still send an email so the user knows the system ran
            subject, html = build_email([])
            send_job_alert(subject, html)
        return 0

    # ── Cap results to top 20 (Gmail has a ~1 MB body limit) ──────────────
    MAX_JOBS = 20
    if len(matched_jobs) > MAX_JOBS:
        print(f"[Main] {len(matched_jobs)} matches found — sending top {MAX_JOBS} by score.")
        matched_jobs = matched_jobs[:MAX_JOBS]

    # ── Step 3: Build email ─────────────────────────────────────────────────
    print(f"\n[Step 3/4] Building HTML email for {len(matched_jobs)} matched jobs...")
    print("-" * 40)
    subject, html_body = build_email(matched_jobs)
    print(f"[Main] Email subject: {subject[:80]}")

    # ── Step 4: Send ────────────────────────────────────────────────────────
    if dry_run:
        print("\n[Step 4/4] DRY RUN — email not sent.")
        # Save HTML to file for preview
        preview_path = Path(__file__).parent / "preview_email.html"
        preview_path.write_text(html_body, encoding="utf-8")
        print(f"[Main] Preview saved to: {preview_path}")
    else:
        print("\n[Step 4/4] Sending email...")
        print("-" * 40)
        success = send_job_alert(subject, html_body)
        if success:
            print(f"\n✓ Done. Sent {len(matched_jobs)} job matches.")
        else:
            print("\n✗ Email failed. Check your .env credentials.")

    print("\n" + "=" * 60)
    return len(matched_jobs)


def main():
    parser = argparse.ArgumentParser(description="Job Alert System")
    parser.add_argument(
        "--test-email", action="store_true",
        help="Send a test email to verify SMTP configuration"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scrape and match but do not send the email (saves preview_email.html)"
    )
    parser.add_argument(
        "--mcf-only", action="store_true",
        help="Scrape MyCareersFuture only (faster, skips Indeed and JobStreet)"
    )
    args = parser.parse_args()

    # Print env warnings
    warnings = _check_env()
    if warnings:
        print("\n⚠  Configuration warnings:")
        for w in warnings:
            print(f"   • {w}")
        print()

    if args.test_email:
        print("[Main] Sending test email...")
        ok = send_test_email()
        sys.exit(0 if ok else 1)

    run(dry_run=args.dry_run, mcf_only=args.mcf_only)


if __name__ == "__main__":
    main()
