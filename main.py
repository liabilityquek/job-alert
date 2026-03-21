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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# ── Load environment variables ─────────────────────────────────────────────
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH, override=False)

# ── Validate .env before importing anything else ───────────────────────────
def _check_env() -> list[str]:
    warnings = []
    if not os.getenv("COMPOSIO_API_KEY"):
        warnings.append("COMPOSIO_API_KEY not set — email sending via Composio will fail.")
    if not os.getenv("EMAIL_RECIPIENTS"):
        warnings.append("EMAIL_RECIPIENTS not set — no recipients configured.")
    return warnings

# ── Imports (after env loaded) ─────────────────────────────────────────────
from scrapers import mycareersfuture, indeed, jobstreet, linkedin
from matcher import match_and_analyse as match_ap
from matcher_underwriting import match_and_analyse as match_uw
from email_builder import build_email
from email_sender import send_job_alert, send_test_email
from sheets_tracker import filter_new_jobs, mark_jobs_sent, log_to_sheet

# ── Underwriting search queries ────────────────────────────────────────────
UW_QUERIES = [
    "underwriting assistant",
    "underwriting executive",
    "underwriting officer",
    "insurance assistant",
    "insurance executive",
    "claims assistant",
]

MAX_JOBS = 25


# ── Scraper helpers ────────────────────────────────────────────────────────
def _scrape_all(queries: list[str] | None, label: str, mcf_only: bool) -> list[dict]:
    """Run all scrapers for the given queries and return deduplicated jobs."""
    all_jobs: list[dict] = []

    try:
        all_jobs.extend(mycareersfuture.scrape(queries))
    except Exception as e:
        print(f"[{label}] MyCareersFuture error: {e}")

    if not mcf_only:
        try:
            all_jobs.extend(indeed.scrape())
        except Exception as e:
            print(f"[{label}] Indeed error: {e}")

        try:
            all_jobs.extend(jobstreet.scrape())
        except Exception as e:
            print(f"[{label}] JobStreet error: {e}")

        try:
            all_jobs.extend(linkedin.scrape(queries))
        except Exception as e:
            print(f"[{label}] LinkedIn error: {e}")

    # Deduplicate
    seen: set[str] = set()
    unique: list[dict] = []
    for job in all_jobs:
        url = job.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(job)
        elif not url:
            key = f"{job['title']}|{job['company']}".lower()
            if key not in seen:
                seen.add(key)
                unique.append(job)

    print(f"[{label}] Total scraped (deduplicated): {len(unique)} jobs")
    return unique


def _enrich_company_info(jobs: list[dict]) -> None:
    """Extract basic company info from job descriptions."""
    for job in jobs:
        desc = (job.get("description", "") or "").lower()
        info_parts = []

        # Company size signals
        if any(kw in desc for kw in ["mnc", "multinational", "global"]):
            info_parts.append("MNC")
        elif any(kw in desc for kw in ["sme", "startup", "start-up"]):
            info_parts.append("SME/Startup")
        elif any(kw in desc for kw in ["government", "statutory board", "public sector"]):
            info_parts.append("Public Sector")

        # Industry signals
        industries = {
            "banking": ["bank", "banking"],
            "insurance": ["insurance", "insurer", "underwriting"],
            "shipping": ["shipping", "maritime", "logistics"],
            "manufacturing": ["manufacturing", "factory"],
            "technology": ["tech", "software", "IT services"],
            "healthcare": ["healthcare", "hospital", "medical"],
            "retail": ["retail", "e-commerce", "ecommerce"],
            "real estate": ["property", "real estate"],
            "energy": ["oil", "gas", "energy"],
        }
        for industry, keywords in industries.items():
            if any(kw in desc for kw in keywords):
                info_parts.append(industry.title())
                break

        if info_parts:
            job["company_info"] = " · ".join(info_parts)


# ── Pipeline runner ────────────────────────────────────────────────────────
def _run_pipeline(
    label: str,
    role_category: str,
    queries: list[str] | None,
    matcher_fn,
    dry_run: bool,
    mcf_only: bool,
) -> int:
    """
    Full pipeline for one role category:
      1. Scrape  2. Match  3. Build email  4. Send

    Returns the number of matched jobs.
    """
    print(f"\n{'=' * 60}")
    print(f"  {label} Pipeline — Starting")
    print(f"{'=' * 60}")

    # Step 1: Scrape
    print(f"\n[{label} Step 1/4] Scraping job portals...")
    print("-" * 40)
    unique_jobs = _scrape_all(queries, label, mcf_only)

    # Step 2: Match
    print(f"\n[{label} Step 2/4] Matching jobs against profile...")
    print("-" * 40)
    matched_jobs = matcher_fn(unique_jobs)

    if not matched_jobs:
        print(f"[{label}] No jobs met the threshold this cycle.")
        if not dry_run:
            subject, html = build_email([], role_category=role_category)
            send_job_alert(subject, html)
        return 0

    # Filter out previously sent jobs
    before_dedup = len(matched_jobs)
    matched_jobs = filter_new_jobs(matched_jobs, label)
    if before_dedup != len(matched_jobs):
        print(f"[{label}] Filtered {before_dedup - len(matched_jobs)} previously sent jobs.")

    # Enrich with company info
    _enrich_company_info(matched_jobs)

    # Guarantee at least 5 LinkedIn jobs in the final list (if available)
    LINKEDIN_MIN = 5
    linkedin_jobs = [j for j in matched_jobs if j.get("source") == "LinkedIn"]
    other_jobs = [j for j in matched_jobs if j.get("source") != "LinkedIn"]

    if linkedin_jobs:
        li_slots = min(LINKEDIN_MIN, len(linkedin_jobs))
        other_slots = MAX_JOBS - li_slots
        final_jobs = other_jobs[:other_slots] + linkedin_jobs[:li_slots]
        # Re-sort by score so the email flows best-match-first
        final_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        matched_jobs = final_jobs
        print(f"[{label}] {len(other_jobs)} non-LinkedIn + {len(linkedin_jobs)} LinkedIn matched — "
              f"reserved {li_slots} LinkedIn slots.")
    elif len(matched_jobs) > MAX_JOBS:
        matched_jobs = matched_jobs[:MAX_JOBS]
        print(f"[{label}] {len(matched_jobs)} matches — sending top {MAX_JOBS}.")

    # Step 3: Build email
    print(f"\n[{label} Step 3/4] Building HTML email for {len(matched_jobs)} jobs...")
    print("-" * 40)
    subject, html_body = build_email(matched_jobs, role_category=role_category)
    print(f"[{label}] Subject: {subject[:80]}")

    # Step 4: Send
    if dry_run:
        print(f"\n[{label} Step 4/4] DRY RUN — email not sent.")
        safe_name = label.lower().replace(" ", "_")
        preview_path = Path(__file__).parent / f"preview_{safe_name}.html"
        preview_path.write_text(html_body, encoding="utf-8")
        print(f"[{label}] Preview: {preview_path}")
    else:
        print(f"\n[{label} Step 4/4] Sending email...")
        print("-" * 40)
        success = send_job_alert(subject, html_body)
        if success:
            print(f"\n[{label}] Done. Sent {len(matched_jobs)} job matches.")
            mark_jobs_sent(matched_jobs, label)
            log_to_sheet(matched_jobs, label)
        else:
            print(f"\n[{label}] Email failed.")

    return len(matched_jobs)


# ── Main orchestrator ──────────────────────────────────────────────────────
def run(dry_run: bool = False, mcf_only: bool = False) -> int:
    """Run both pipelines (AP/Finance + Underwriting) in parallel."""
    print("=" * 60)
    print("  Job Alert System — Starting Run (2 pipelines)")
    print("=" * 60)

    results = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(
                _run_pipeline,
                "AP/Finance", "AP / Finance",
                None,       # uses TARGET_ROLES from resume_profile
                match_ap,
                dry_run, mcf_only,
            ): "AP/Finance",
            pool.submit(
                _run_pipeline,
                "Underwriting", "Underwriting",
                UW_QUERIES,
                match_uw,
                dry_run, mcf_only,
            ): "Underwriting",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                count = future.result()
                results[name] = count
            except Exception as e:
                print(f"\n[Main] {name} pipeline error: {e}")
                results[name] = 0

    print("\n" + "=" * 60)
    print("  Final Summary")
    print("=" * 60)
    for name, count in results.items():
        print(f"  {name}: {count} jobs sent")
    print("=" * 60)

    return sum(results.values())


def main():
    parser = argparse.ArgumentParser(description="Job Alert System")
    parser.add_argument(
        "--test-email", action="store_true",
        help="Send a test email to verify SMTP configuration"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scrape and match but do not send the email (saves preview HTML)"
    )
    parser.add_argument(
        "--mcf-only", action="store_true",
        help="Scrape MyCareersFuture only (faster, skips other portals)"
    )
    args = parser.parse_args()

    warnings = _check_env()
    if warnings:
        print("\n  Configuration warnings:")
        for w in warnings:
            print(f"   * {w}")
        print()

    if args.test_email:
        print("[Main] Sending test email...")
        ok = send_test_email()
        sys.exit(0 if ok else 1)

    run(dry_run=args.dry_run, mcf_only=args.mcf_only)


if __name__ == "__main__":
    main()
