"""
JobStreet Singapore scraper.
Uses their public search page and parses JSON-LD structured data.
"""

import re
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

BASE_URL = "https://www.jobstreet.com.sg"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-SG,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.jobstreet.com.sg/",
}
CUTOFF_DAYS = 14
SEARCH_QUERIES = [
    "accounts-payable",
    "finance-executive",
    "ap-officer",
    "accounts-executive",
]


def _within_cutoff(date_str: str) -> bool:
    if not date_str:
        return True
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=CUTOFF_DAYS)
        return dt >= cutoff
    except Exception:
        return True


def _scrape_query(query: str, max_pages: int = 3) -> list[dict]:
    jobs = []
    seen = set()

    for page_num in range(1, max_pages + 1):
        url = f"{BASE_URL}/jobs/{query}-jobs"
        params = {"page": page_num, "sortmode": "ListedDate"}
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[JobStreet] Error on page {page_num} for '{query}': {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try JSON-LD structured data first (most reliable)
        json_ld_blocks = soup.find_all("script", type="application/ld+json")
        for block in json_ld_blocks:
            try:
                data = json.loads(block.string or "")
                if isinstance(data, list):
                    items = data
                elif data.get("@type") == "ItemList":
                    items = [e.get("item", {}) for e in data.get("itemListElement", [])]
                else:
                    items = [data]

                for item in items:
                    if item.get("@type") != "JobPosting":
                        continue
                    job_url = item.get("url", "")
                    if job_url in seen:
                        continue
                    seen.add(job_url)

                    posted = item.get("datePosted", "")
                    if not _within_cutoff(posted):
                        continue

                    salary_obj = item.get("baseSalary", {})
                    sal_val = salary_obj.get("value", {})
                    if isinstance(sal_val, dict):
                        sal_min = sal_val.get("minValue", "")
                        sal_max = sal_val.get("maxValue", "")
                        salary = f"SGD {sal_min:,} – {sal_max:,}" if sal_min and sal_max else "Not disclosed"
                    else:
                        salary = str(sal_val) if sal_val else "Not disclosed"

                    location_obj = item.get("jobLocation", {})
                    if isinstance(location_obj, list):
                        location_obj = location_obj[0] if location_obj else {}
                    address = location_obj.get("address", {})
                    city = address.get("addressLocality", "Singapore")

                    description = item.get("description", "") or ""
                    description = re.sub(r"<[^>]+>", " ", description)  # strip HTML tags

                    jobs.append({
                        "source": "JobStreet",
                        "title": item.get("title", "N/A"),
                        "company": item.get("hiringOrganization", {}).get("name", "N/A"),
                        "location": city or "Singapore",
                        "salary": salary,
                        "url": job_url,
                        "description": description[:2000],
                        "employment_type": item.get("employmentType", ""),
                        "posted_date": posted,
                    })
            except Exception as e:
                print(f"[JobStreet] JSON-LD parse error: {e}")
                continue

        # Fallback: parse job cards from HTML if no JSON-LD found
        if not jobs:
            cards = soup.find_all("article", {"data-card-type": "JobCard"})
            for card in cards:
                try:
                    title_el = card.find("h1") or card.find("h2") or card.find(
                        "a", {"data-automation": "jobTitle"})
                    company_el = card.find("a", {"data-automation": "jobCompany"})
                    location_el = card.find("span", {"data-automation": "jobLocation"})
                    link_el = card.find("a", href=re.compile(r"/job/"))
                    date_el = card.find("time")

                    title = title_el.get_text(strip=True) if title_el else "N/A"
                    company = company_el.get_text(strip=True) if company_el else "N/A"
                    location = location_el.get_text(strip=True) if location_el else "Singapore"
                    href = link_el["href"] if link_el and link_el.get("href") else ""
                    job_url = (BASE_URL + href) if href.startswith("/") else href
                    posted = date_el.get("datetime", "") if date_el else ""

                    if job_url in seen:
                        continue
                    seen.add(job_url)
                    if not _within_cutoff(posted):
                        continue

                    jobs.append({
                        "source": "JobStreet",
                        "title": title,
                        "company": company,
                        "location": location,
                        "salary": "Not disclosed",
                        "url": job_url,
                        "description": "",
                        "employment_type": "",
                        "posted_date": posted,
                    })
                except Exception:
                    continue

        time.sleep(2)

    return jobs


def scrape() -> list[dict]:
    """Scrape JobStreet Singapore for AP/Finance roles."""
    all_jobs = []
    seen_urls = set()

    for query in SEARCH_QUERIES:
        print(f"[JobStreet] Searching: {query}")
        jobs = _scrape_query(query)
        for job in jobs:
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
        time.sleep(2)

    print(f"[JobStreet] Total unique jobs found: {len(all_jobs)}")
    return all_jobs
