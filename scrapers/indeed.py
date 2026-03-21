"""
Indeed Singapore scraper — uses their public job search page.
Targets Singapore-based AP/Finance roles posted in the last 14 days.
"""

import re
import time
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BASE_URL = "https://sg.indeed.com"
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
SEARCH_QUERIES = [
    "accounts payable",
    "AP officer finance",
    "accounts payable executive Singapore",
    "finance executive accounts payable",
]


def _parse_posted_date(text: str) -> bool:
    """Return True if the 'X days ago' text is within the 14-day cutoff."""
    if not text:
        return True
    text = text.lower().strip()
    if "just posted" in text or "today" in text or "hours ago" in text:
        return True
    match = re.search(r"(\d+)\s*day", text)
    if match:
        days_ago = int(match.group(1))
        return days_ago <= CUTOFF_DAYS
    return True  # include if unparseable


def _scrape_query(query: str, max_pages: int = 3) -> list[dict]:
    jobs = []
    seen = set()

    for page_num in range(max_pages):
        start = page_num * 10
        url = f"{BASE_URL}/jobs"
        params = {
            "q": query,
            "l": "Singapore",
            "sort": "date",
            "fromage": str(CUTOFF_DAYS),
            "start": str(start),
        }
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[Indeed] Error on page {page_num} for '{query}': {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Indeed uses data-jk attribute for job keys
        job_cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|tapItem"))
        if not job_cards:
            job_cards = soup.find_all("li", class_=re.compile(r"css-5lfssm|result"))

        for card in job_cards:
            try:
                # Title
                title_el = card.find("h2", class_=re.compile(r"jobTitle")) or \
                           card.find("a", {"data-jk": True})
                title = title_el.get_text(strip=True) if title_el else "N/A"

                # Company
                company_el = card.find("span", {"data-testid": "company-name"}) or \
                             card.find("span", class_=re.compile(r"companyName"))
                company = company_el.get_text(strip=True) if company_el else "N/A"

                # Location
                location_el = card.find("div", {"data-testid": "text-location"}) or \
                              card.find("div", class_=re.compile(r"companyLocation"))
                location = location_el.get_text(strip=True) if location_el else "Singapore"

                # Only include Singapore roles
                if "singapore" not in location.lower() and location != "N/A":
                    continue

                # Job URL
                link_el = card.find("a", href=re.compile(r"/rc/clk|/pagead|/jobs/"))
                if not link_el:
                    link_el = card.find("a", {"data-jk": True})
                href = link_el["href"] if link_el and link_el.get("href") else ""
                job_url = (BASE_URL + href) if href.startswith("/") else href

                if job_url in seen:
                    continue
                seen.add(job_url)

                # Date posted
                date_el = card.find("span", class_=re.compile(r"date|posted"))
                posted_text = date_el.get_text(strip=True) if date_el else ""
                if not _parse_posted_date(posted_text):
                    continue

                # Salary
                salary_el = card.find("div", class_=re.compile(r"salary|compensation"))
                salary = salary_el.get_text(strip=True) if salary_el else "Not disclosed"

                # Snippet / description
                snippet_el = card.find("div", class_=re.compile(r"summary|snippet"))
                description = snippet_el.get_text(strip=True) if snippet_el else ""

                jobs.append({
                    "source": "Indeed",
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "url": job_url,
                    "description": description,
                    "employment_type": "",
                    "posted_date": posted_text,
                })
            except Exception as e:
                print(f"[Indeed] Error parsing card: {e}")
                continue

        time.sleep(1.5)  # polite delay

    return jobs


def scrape() -> list[dict]:
    """Scrape Indeed Singapore for AP/Finance roles."""
    all_jobs = []
    seen_urls = set()

    for query in SEARCH_QUERIES:
        print(f"[Indeed] Searching: {query}")
        jobs = _scrape_query(query)
        for job in jobs:
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
        time.sleep(2)

    print(f"[Indeed] Total unique jobs found: {len(all_jobs)}")
    return all_jobs
