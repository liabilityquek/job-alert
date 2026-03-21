"""
LinkedIn Singapore scraper — uses LinkedIn's public job search page.
No login required. Parses job cards from the public listings.

Note: LinkedIn may rate-limit or block requests from cloud IPs.
This scraper is best-effort and gracefully returns [] on failure.
"""

import re
import time
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from resume_profile import TARGET_ROLES

BASE_URL = "https://www.linkedin.com/jobs/search"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-SG,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
CUTOFF_DAYS = 14
# LinkedIn uses f_TPR for time filter: r604800 = past week, r1209600 = past 14 days
TIME_FILTER = "r1209600"
# LinkedIn geoId for Singapore
SINGAPORE_GEO_ID = "102454443"


def _fetch_full_description(job_url: str) -> str:
    """Fetch the full job description from a LinkedIn job page."""
    try:
        resp = requests.get(job_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        desc_el = None

        # Try selector 1: div with class description__text or show-more-less-html__markup
        desc_el = soup.find("div", class_=re.compile(
            r"description__text|show-more-less-html__markup"
        ))

        # Try selector 2: section with class description
        if not desc_el:
            desc_el = soup.find("section", class_=re.compile(r"description"))

        # Try selector 3: any div with class job-description
        if not desc_el:
            desc_el = soup.find("div", class_=re.compile(r"job-description"))

        if not desc_el:
            return ""

        text = desc_el.get_text(separator=" ", strip=True)
        return text[:2000]
    except Exception:
        return ""


def _scrape_query(query: str, max_pages: int = 2) -> list[dict]:
    """Scrape LinkedIn public job listings for a single query."""
    jobs = []
    seen = set()

    for page_num in range(max_pages):
        start = page_num * 25  # LinkedIn uses 25 results per page
        params = {
            "keywords": query,
            "location": "Singapore",
            "geoId": SINGAPORE_GEO_ID,
            "f_TPR": TIME_FILTER,
            "sortBy": "DD",  # sort by date
            "start": str(start),
        }
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code == 429:
                print(f"[LinkedIn] Rate limited on page {page_num} for '{query}'")
                break
            resp.raise_for_status()
        except Exception as e:
            print(f"[LinkedIn] Error on page {page_num} for '{query}': {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # LinkedIn public pages use specific card classes
        job_cards = soup.find_all("div", class_=re.compile(
            r"base-card|job-search-card|base-search-card"
        ))
        if not job_cards:
            # Try alternative selectors
            job_cards = soup.find_all("li", class_=re.compile(
                r"jobs-search__result|result-card"
            ))

        if not job_cards:
            break

        for card in job_cards:
            try:
                # Title
                title_el = (
                    card.find("h3", class_=re.compile(r"base-search-card__title"))
                    or card.find("h3")
                    or card.find("span", class_=re.compile(r"sr-only"))
                )
                title = title_el.get_text(strip=True) if title_el else "N/A"

                # Company
                company_el = (
                    card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
                    or card.find("a", class_=re.compile(r"hidden-nested-link"))
                )
                company = company_el.get_text(strip=True) if company_el else "N/A"

                # Location
                location_el = card.find(
                    "span", class_=re.compile(r"job-search-card__location")
                )
                location = location_el.get_text(strip=True) if location_el else "Singapore"

                # Only include Singapore roles
                if "singapore" not in location.lower():
                    continue

                # Job URL
                link_el = card.find("a", href=re.compile(r"linkedin\.com/jobs/view"))
                if not link_el:
                    link_el = card.find("a", class_=re.compile(r"base-card__full-link"))
                if not link_el:
                    link_el = card.find("a", href=True)
                href = link_el["href"] if link_el and link_el.get("href") else ""
                # Clean tracking params from URL
                job_url = href.split("?")[0] if href else ""

                if not job_url or job_url in seen:
                    continue
                seen.add(job_url)

                # Date posted
                date_el = card.find("time")
                posted = ""
                if date_el:
                    posted = date_el.get("datetime", "") or date_el.get_text(strip=True)

                # Check date cutoff
                if posted and "T" not in posted:
                    # Text like "2 weeks ago" — just include it
                    pass
                elif posted:
                    try:
                        dt = datetime.fromisoformat(posted.replace("Z", "+00:00"))
                        cutoff = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
                        if dt < cutoff:
                            continue
                    except Exception:
                        pass

                # Salary (LinkedIn rarely shows salary on public pages)
                salary_el = card.find(
                    "span", class_=re.compile(r"job-search-card__salary")
                )
                salary = salary_el.get_text(strip=True) if salary_el else "Not disclosed"

                # Description snippet
                desc_el = card.find(
                    "p", class_=re.compile(r"job-search-card__snippet")
                )
                description = desc_el.get_text(strip=True) if desc_el else ""

                jobs.append({
                    "source": "LinkedIn",
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "url": job_url,
                    "description": description,
                    "employment_type": "",
                    "posted_date": posted,
                })

                # Attempt to fetch the full job description
                full_desc = _fetch_full_description(job_url)
                if full_desc:
                    jobs[-1]["description"] = full_desc
                time.sleep(1)  # polite delay after each fetch
            except Exception as e:
                print(f"[LinkedIn] Error parsing card: {e}")
                continue

        time.sleep(2)  # polite delay

    return jobs


def scrape(queries: list[str] | None = None) -> list[dict]:
    """Scrape LinkedIn for Singapore jobs.
    If queries is None, uses TARGET_ROLES from resume profile."""
    all_jobs = []
    seen_urls = set()

    # Use top 4 queries to avoid rate limiting
    queries = (queries or TARGET_ROLES)[:4]

    for query in queries:
        print(f"[LinkedIn] Searching: {query}")
        jobs = _scrape_query(query)
        for job in jobs:
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
        time.sleep(3)  # longer delay between queries for LinkedIn

    print(f"[LinkedIn] Total unique jobs found: {len(all_jobs)}")
    return all_jobs
