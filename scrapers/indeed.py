"""
Indeed Singapore scraper — uses Firecrawl to scrape Indeed search pages.
Targets Singapore-based AP/Finance roles posted in the last 14 days.
"""

import os
import re
import time
from firecrawl import FirecrawlApp

BASE_URL = "https://sg.indeed.com"
CUTOFF_DAYS = 14
SEARCH_QUERIES = [
    "accounts payable",
    "AP officer finance",
    "accounts payable executive Singapore",
    "finance executive accounts payable",
]


def _get_firecrawl() -> FirecrawlApp:
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        raise EnvironmentError("FIRECRAWL_API_KEY not set")
    return FirecrawlApp(api_key=api_key)


def _parse_jobs_from_markdown(md: str) -> list[dict]:
    """Parse job listings from Indeed's markdown output."""
    jobs = []
    if not md:
        return jobs

    # Indeed markdown has job blocks starting with ## [Title](url)
    # or patterns like: ## [Job Title](link)\nCompany\nLocation
    blocks = re.split(r'(?=##\s*\[)', md)

    for block in blocks:
        try:
            # Extract title and URL: ## [Title](url)
            title_match = re.search(r'##\s*\[([^\]]+)\]\(([^)]+)\)', block)
            if not title_match:
                continue

            title = title_match.group(1).strip()
            raw_url = title_match.group(2).strip()

            # Build full URL
            if raw_url.startswith("/"):
                job_url = BASE_URL + raw_url
            elif raw_url.startswith("http"):
                job_url = raw_url
            else:
                continue

            # Clean tracking params but keep job key
            job_url = job_url.split("&xkcb=")[0]

            # Extract remaining text after title
            rest = block[title_match.end():]
            lines = [l.strip() for l in rest.split("\n") if l.strip()]

            # Company is usually the first non-empty line after title
            company = "N/A"
            company_found = False
            location = "Singapore"
            salary = "Not disclosed"
            description = ""
            posted_text = ""

            for line in lines:
                # Skip nav/filter lines
                if any(skip in line.lower() for skip in [
                    "skip to", "edit location", "find jobs", "all salaries",
                    "upload your", "sort by", "relevance", "page ", "next",
                ]):
                    continue

                # Detect salary patterns
                if re.search(r'\$[\d,]+', line) and not company_found:
                    salary = line
                    continue

                # Detect posted date
                if re.search(r'(posted|ago|today|just)', line, re.I):
                    posted_text = line
                    continue

                # First meaningful line is company
                if company == "N/A" and len(line) > 1 and not line.startswith("|"):
                    # Clean HTML remnants from company name
                    clean = re.sub(r'<[^>]+>', '', line).strip().strip('|').strip()
                    if clean:
                        company = clean
                    else:
                        company = line
                    company_found = True
                    continue

                # Next line could be location
                if company_found and "singapore" in line.lower():
                    location = line
                    continue

                # Remaining is description
                if len(line) > 20:
                    description += " " + line

            # Only include Singapore roles
            if "singapore" not in location.lower() and "singapore" not in block.lower():
                continue

            jobs.append({
                "source": "Indeed",
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "url": job_url,
                "description": description.strip()[:2000],
                "employment_type": "",
                "posted_date": posted_text,
            })
        except Exception as e:
            print(f"[Indeed] Error parsing block: {e}")
            continue

    return jobs


def _scrape_query(app: FirecrawlApp, query: str, max_pages: int = 2) -> list[dict]:
    """Scrape Indeed search results using Firecrawl."""
    jobs = []
    seen = set()

    for page_num in range(max_pages):
        start = page_num * 10
        url = (
            f"{BASE_URL}/jobs?q={query.replace(' ', '+')}"
            f"&l=Singapore&sort=date&fromage={CUTOFF_DAYS}&start={start}"
        )
        try:
            result = app.scrape(url, formats=["markdown"])
            md = getattr(result, "markdown", "") or ""
            if not md:
                print(f"[Indeed] Empty result for '{query}' page {page_num}")
                break

            parsed = _parse_jobs_from_markdown(md)
            for job in parsed:
                if job["url"] not in seen:
                    seen.add(job["url"])
                    jobs.append(job)

        except Exception as e:
            print(f"[Indeed] Error on page {page_num} for '{query}': {e}")
            break

        time.sleep(1)

    return jobs


def scrape(queries: list[str] | None = None) -> list[dict]:
    """Scrape Indeed Singapore for jobs using Firecrawl."""
    try:
        app = _get_firecrawl()
    except EnvironmentError as e:
        print(f"[Indeed] {e} — skipping Indeed scraper")
        return []

    search_terms = queries or SEARCH_QUERIES
    all_jobs = []
    seen_urls = set()

    for query in search_terms:
        print(f"[Indeed] Searching: {query}")
        jobs = _scrape_query(app, query)
        for job in jobs:
            if job["url"] and job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
        time.sleep(1)

    print(f"[Indeed] Total unique jobs found: {len(all_jobs)}")
    return all_jobs
