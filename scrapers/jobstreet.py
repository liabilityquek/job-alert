"""
JobStreet Singapore scraper — currently disabled.
JobStreet (SEEK platform) blocks all automated access including Firecrawl.
This scraper returns an empty list to avoid wasting Firecrawl credits.
"""


def scrape(queries: list[str] | None = None) -> list[dict]:
    """JobStreet is not scrapeable — returns empty list."""
    print("[JobStreet] Skipped — site blocks automated access")
    return []
