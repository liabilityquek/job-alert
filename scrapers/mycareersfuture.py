"""
MyCareersFuture (Singapore Gov) scraper — uses the official public API.
Endpoint: https://api.mycareersfuture.gov.sg/v2/jobs
"""

import requests
from datetime import datetime, timedelta, timezone
from resume_profile import TARGET_ROLES

MCF_API = "https://api.mycareersfuture.gov.sg/v2/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobAlertBot/1.0)",
    "Accept": "application/json",
}

CUTOFF_DAYS = 14


def _posted_within_cutoff(posted_str: str) -> bool:
    """Return True if the job was posted within the last CUTOFF_DAYS days."""
    if not posted_str:
        return False
    try:
        posted = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
        return posted >= cutoff
    except Exception:
        return True  # include if we can't parse


def _fetch_for_query(query: str, max_pages: int = 3) -> list[dict]:
    jobs = []
    for page in range(max_pages):
        params = {
            "search": query,
            "limit": 100,
            "page": page,
            "sortBy": "new_posting_date",
        }
        try:
            resp = requests.get(MCF_API, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[MCF] Error fetching page {page} for '{query}': {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for job in results:
            posted = job.get("metadata", {}).get("newPostingDate", "") or job.get(
                "metadata", {}).get("originalPostingDate", ""
            )
            if not _posted_within_cutoff(posted):
                continue

            # Extract fields (title is top-level, not nested under position)
            title = job.get("title", "N/A")
            company = (
                job.get("postedCompany", {}).get("name", None)
                or job.get("hiringCompany", {}).get("name", "N/A")
            )
            location = "Singapore"
            salary_min = job.get("salary", {}).get("minimum", None)
            salary_max = job.get("salary", {}).get("maximum", None)
            salary = (
                f"SGD {salary_min:,} – {salary_max:,}/month"
                if salary_min and salary_max
                else "Not disclosed"
            )
            uuid = job.get("uuid", "")
            url = f"https://www.mycareersfuture.gov.sg/job/{uuid}" if uuid else ""

            # Strip HTML from description
            raw_desc = job.get("description", "") or ""
            import re as _re
            clean_desc = _re.sub(r"<[^>]+>", " ", raw_desc)
            clean_desc = _re.sub(r"\s+", " ", clean_desc).strip()

            # Append skills list for better keyword matching
            skills_list = job.get("skills", []) or []
            skills_text = " ".join(
                s.get("skill", "") if isinstance(s, dict) else str(s)
                for s in skills_list
            )
            description = f"{clean_desc} {skills_text}".strip()

            employment_type = job.get("employmentTypes", [{}])
            emp_type = employment_type[0].get("employmentType", "") if employment_type else ""

            jobs.append({
                "source": "MyCareersFuture",
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "url": url,
                "description": description,
                "employment_type": emp_type,
                "posted_date": posted,
            })

    return jobs


def scrape(queries: list[str] | None = None) -> list[dict]:
    """Scrape MyCareersFuture for Singapore jobs.
    If queries is None, uses TARGET_ROLES from resume profile."""
    search_terms = (queries or TARGET_ROLES)[:6]
    all_jobs = []
    seen_urls = set()

    for role in search_terms:
        print(f"[MCF] Searching: {role}")
        jobs = _fetch_for_query(role)
        for job in jobs:
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)

    print(f"[MCF] Total unique jobs found: {len(all_jobs)}")
    return all_jobs
