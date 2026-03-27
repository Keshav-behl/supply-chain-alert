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
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Keywords that signal supply chain risk for Indian SME manufacturers
# Expand this list as you learn more about your target users' supply chains
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
# FETCHER
# ─────────────────────────────────────────────

def fetch_news_for_keyword(keyword: str, from_date: str) -> list[dict]:
    """
    Fetches articles from NewsAPI for a single keyword.
    Returns a list of raw article dicts.
    """
    params = {
        "q": keyword,
        "from": from_date,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": 5,          # 5 articles per keyword — enough signal, saves API quota
        "apiKey": NEWSAPI_KEY,
    }

    try:
        response = requests.get(NEWSAPI_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            print(f"  [WARN] NewsAPI returned non-ok status for '{keyword}': {data.get('message')}")
            return []

        articles = data.get("articles", [])
        print(f"  [OK] '{keyword}' → {len(articles)} articles found")
        return articles

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Request failed for '{keyword}': {e}")
        return []


def deduplicate_articles(articles: list[dict]) -> list[dict]:
    """
    Removes duplicate articles by URL.
    Same story can appear under multiple keyword searches.
    """
    seen_urls = set()
    unique = []
    for article in articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)
    return unique


def parse_article(raw: dict) -> dict:
    """
    Extracts only the fields we need from a raw NewsAPI article.
    Keeps the data model clean for the risk scorer downstream.
    """
    return {
        "title": raw.get("title", ""),
        "description": raw.get("description", ""),
        "url": raw.get("url", ""),
        "source": raw.get("source", {}).get("name", "Unknown"),
        "published_at": raw.get("publishedAt", ""),
        "content_snippet": raw.get("content", "")[:300] if raw.get("content") else "",
    }


def fetch_all_risk_news() -> list[dict]:
    """
    Main function. Fetches news for all risk keywords,
    deduplicates, parses, and returns clean article list.

    Returns:
        List of parsed article dicts ready for risk scoring.
    """
    if not NEWSAPI_KEY:
        raise EnvironmentError(
            "NEWSAPI_KEY not found. Add it to your .env file.\n"
            "Get a free key at: https://newsapi.org/register"
        )

    from_date = (datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    print(f"\n[NEWS FETCHER] Scanning {len(RISK_KEYWORDS)} keywords from {from_date}...\n")

    raw_articles = []
    for keyword in RISK_KEYWORDS:
        articles = fetch_news_for_keyword(keyword, from_date)
        raw_articles.extend(articles)

    # Deduplicate before parsing
    unique_articles = deduplicate_articles(raw_articles)
    print(f"\n[NEWS FETCHER] {len(raw_articles)} total → {len(unique_articles)} unique articles after dedup\n")

    # Parse to clean schema
    parsed = [parse_article(a) for a in unique_articles]

    return parsed


# ─────────────────────────────────────────────
# QUICK TEST — run this file directly to verify
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
