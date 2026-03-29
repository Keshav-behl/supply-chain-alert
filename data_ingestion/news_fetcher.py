"""
news_fetcher.py
---------------
Fetches India-relevant supply chain disruption news using NewsAPI.
Filters by keywords relevant to SME manufacturing risks.

Setup:
    pip install requests python-dotenv
    Add NEWSAPI_KEY to your .env file
    Get free key at: https://newsapi.org/register
"""

import os
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Low quality / unreliable sources to ignore
BLOCKED_SOURCES = [
    "theeconomiccollapseblog.com",
    "newsbreakapp.com",
    "beforeitsnews.com",
    "zerohedge.com",
    "naturalnews.com",
    "infowars.com",
]

# Blocked URLs (NewsAPI returns removed articles with this URL)
BLOCKED_URLS = [
    "https://removed.com",
    "",
]

# Keywords that signal supply chain risk for Indian SME manufacturers
RISK_KEYWORDS = [
    "port strike India",
    "port congestion Mumbai",
    "JNPT delay",
    "flood Maharashtra",
    "flood Gujarat",
    "flood Punjab",
    "highway blockade India",
    "fuel shortage India",
    "coal shortage India",
    "steel shortage India",
    "freight rate increase India",
    "supply chain disruption India",
    "truck strike India",
    "railway freight disruption India",
    "cyclone India manufacturing",
]

# How many days back to look for news
LOOKBACK_DAYS = 2


# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────

def is_blocked_source(article: dict) -> bool:
    """Returns True if article is from a blocked low-quality source."""
    source_name = (article.get("source", {}).get("name") or "").lower()
    source_id   = (article.get("source", {}).get("id")   or "").lower()
    url         = (article.get("url") or "").lower()

    for blocked in BLOCKED_SOURCES:
        blocked = blocked.lower()
        if blocked in source_name or blocked in source_id or blocked in url:
            return True
    return False


def is_blocked_url(article: dict) -> bool:
    """Returns True if article URL is in the blocked list."""
    url = article.get("url", "").strip()
    return url in BLOCKED_URLS or not url


def is_valid_article(article: dict) -> bool:
    """
    Returns True if article passes all quality filters.
    Filters out: blocked sources, removed articles, articles with no title.
    """
    if is_blocked_source(article):
        return False
    if is_blocked_url(article):
        return False
    if not article.get("title") or article.get("title") == "[Removed]":
        return False
    if not article.get("description"):
        return False
    return True


# ─────────────────────────────────────────────
# FETCHER
# ─────────────────────────────────────────────

def fetch_news_for_keyword(keyword: str, from_date: str) -> list[dict]:
    """
    Fetches articles from NewsAPI for a single keyword.
    Applies quality filters before returning.
    """
    params = {
        "q":        keyword,
        "from":     from_date,
        "language": "en",
        "sortBy":   "relevancy",
        "pageSize": 5,
        "apiKey":   NEWSAPI_KEY,
    }

    try:
        response = requests.get(NEWSAPI_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            print(f"  [WARN] NewsAPI non-ok for '{keyword}': {data.get('message')}")
            return []

        raw_articles = data.get("articles", [])

        # Apply quality filter here
        filtered = [a for a in raw_articles if is_valid_article(a)]
        blocked  = len(raw_articles) - len(filtered)

        if blocked > 0:
            print(f"  [OK] '{keyword}' → {len(filtered)} articles ({blocked} blocked)")
        else:
            print(f"  [OK] '{keyword}' → {len(filtered)} articles found")

        return filtered

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Request failed for '{keyword}': {e}")
        return []


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """Removes duplicate articles by URL."""
    seen_urls = set()
    unique = []
    for article in articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)
    return unique


def parse_article(raw: dict) -> dict:
    """Extracts only the fields we need from a raw NewsAPI article."""
    return {
        "title":          raw.get("title", ""),
        "description":    raw.get("description", ""),
        "url":            raw.get("url", ""),
        "source":         raw.get("source", {}).get("name", "Unknown"),
        "published_at":   raw.get("publishedAt", ""),
        "content_snippet": raw.get("content", "")[:300] if raw.get("content") else "",
    }


def fetch_all_risk_news() -> list[dict]:
    """
    Main function. Fetches news for all risk keywords,
    filters low quality sources, deduplicates, and returns clean articles.
    """
    if not NEWSAPI_KEY:
        raise EnvironmentError(
            "NEWSAPI_KEY not found. Add it to your .env file.\n"
            "Get a free key at: https://newsapi.org/register"
        )

    from_date = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    print(f"\n[NEWS FETCHER] Scanning {len(RISK_KEYWORDS)} keywords from {from_date}...\n")

    raw_articles = []
    for keyword in RISK_KEYWORDS:
        articles = fetch_news_for_keyword(keyword, from_date)
        raw_articles.extend(articles)

    unique_articles = deduplicate_articles(raw_articles)
    print(f"\n[NEWS FETCHER] {len(raw_articles)} total → {len(unique_articles)} unique articles after dedup\n")

    parsed = [parse_article(a) for a in unique_articles]
    return parsed


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    articles = fetch_all_risk_news()

    if not articles:
        print("No articles found. Check your API key or try different keywords.")
    else:
        print(f"{'─'*60}")
        print(f"SAMPLE OUTPUT — First 3 Articles")
        print(f"{'─'*60}")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n[{i}] {article['title']}")
            print(f"    Source : {article['source']}")
            print(f"    Date   : {article['published_at']}")
            print(f"    URL    : {article['url']}")
            print(f"    Desc   : {article['description'][:120]}...")