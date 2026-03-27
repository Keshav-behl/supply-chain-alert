"""
risk_scorer.py
--------------
Scores each news article for supply chain disruption risk.

Scoring Formula:
    Risk Score = Severity x Proximity x Sector Relevance
    Max Score  = 5 x 3 x 3 = 45
    Alert Threshold = 25 (configurable in .env)

Three scoring axes:
    1. Severity       — how bad is the disruption? (1-5)
    2. Proximity      — how close to Indian manufacturing hubs? (1-3)
    3. Sector         — does it affect common SME raw materials? (1-3)
"""

import os
from dotenv import load_dotenv

load_dotenv()

RISK_THRESHOLD = int(os.getenv("RISK_SCORE_THRESHOLD", 25))


# ─────────────────────────────────────────────
# SEVERITY KEYWORDS (Axis 1 — Score 1 to 5)
# ─────────────────────────────────────────────
# How destructive is the event?
# 5 = catastrophic, 1 = minor inconvenience

SEVERITY_KEYWORDS = {
    5: [
        "cyclone", "earthquake", "flood", "tsunami",
        "complete shutdown", "total blockade", "national strike",
        "port closure", "rail shutdown", "highway closed",
    ],
    4: [
        "major strike", "severe disruption", "significant delay",
        "fuel crisis", "power outage", "factory fire",
        "port congestion", "cargo backlog",
    ],
    3: [
        "strike", "protest", "disruption", "shortage",
        "delay", "blockade", "slowdown", "backlog",
    ],
    2: [
        "warning", "alert", "risk", "concern",
        "possible delay", "minor disruption", "partial",
    ],
    1: [
        "watch", "monitor", "potential", "slight",
        "marginal", "low impact",
    ],
}

# ─────────────────────────────────────────────
# PROXIMITY KEYWORDS (Axis 2 — Score 1 to 3)
# ─────────────────────────────────────────────
# Is the disruption near Indian manufacturing hubs?
# 3 = direct hit on major hub, 1 = far/international

PROXIMITY_KEYWORDS = {
    3: [
        # Major manufacturing + port states
        "mumbai", "pune", "gujarat", "surat", "ahmedabad",
        "ludhiana", "punjab", "rajkot", "vadodara",
        "chennai", "coimbatore", "bengaluru", "bangalore",
        "jnpt", "nhava sheva", "kandla", "mundra",
        "delhi", "ncr", "faridabad", "gurgaon",
        "maharashtra", "tamil nadu", "karnataka",
    ],
    2: [
        # Secondary manufacturing states
        "hyderabad", "telangana", "andhra",
        "kolkata", "west bengal", "odisha",
        "rajasthan", "madhya pradesh", "uttar pradesh",
        "india", "indian", "domestic",
    ],
    1: [
        # International — still relevant but lower proximity
        "china", "global", "international", "worldwide",
        "suez", "shipping lane", "freight", "import",
    ],
}

# ─────────────────────────────────────────────
# SECTOR KEYWORDS (Axis 3 — Score 1 to 3)
# ─────────────────────────────────────────────
# Does it affect materials SME manufacturers commonly use?
# 3 = core raw materials, 1 = tangentially related

SECTOR_KEYWORDS = {
    3: [
        # Core SME raw materials
        "steel", "iron", "aluminium", "aluminum", "copper",
        "coal", "coke", "plastic", "polymer", "resin",
        "cotton", "yarn", "fabric", "textile",
        "cement", "chemical", "solvent",
        "fuel", "diesel", "petrol", "crude",
    ],
    2: [
        # Logistics and supply chain infrastructure
        "freight", "logistics", "cargo", "shipping",
        "truck", "transport", "warehouse", "supply chain",
        "raw material", "inventory", "procurement",
        "port", "rail", "highway",
    ],
    1: [
        # Broader economic signals
        "manufacturing", "factory", "production", "industry",
        "export", "import", "trade", "economy",
        "msme", "sme", "small business",
    ],
}


# ─────────────────────────────────────────────
# SCORING FUNCTIONS
# ─────────────────────────────────────────────

def get_text(article: dict) -> str:
    """Combines title + description into one lowercase string for matching."""
    title = article.get("title", "") or ""
    description = article.get("description", "") or ""
    return (title + " " + description).lower()


def score_severity(text: str) -> int:
    """
    Returns severity score (1-5) based on keyword matching.
    Higher severity keywords take priority.
    """
    for score in sorted(SEVERITY_KEYWORDS.keys(), reverse=True):
        for keyword in SEVERITY_KEYWORDS[score]:
            if keyword in text:
                return score
    return 1  # Default — minimal severity


def score_proximity(text: str) -> int:
    """
    Returns proximity score (1-3) based on location keywords.
    Closer to Indian manufacturing hubs = higher score.
    """
    for score in sorted(PROXIMITY_KEYWORDS.keys(), reverse=True):
        for keyword in PROXIMITY_KEYWORDS[score]:
            if keyword in text:
                return score
    return 1  # Default — not near India


def score_sector(text: str) -> int:
    """
    Returns sector relevance score (1-3).
    More relevant to SME raw materials = higher score.
    """
    for score in sorted(SECTOR_KEYWORDS.keys(), reverse=True):
        for keyword in SECTOR_KEYWORDS[score]:
            if keyword in text:
                return score
    return 1  # Default — tangential relevance


def score_article(article: dict) -> dict:
    """
    Scores a single article across all three axes.
    Returns the article enriched with scoring data.
    """
    text = get_text(article)

    severity  = score_severity(text)
    proximity = score_proximity(text)
    sector    = score_sector(text)

    total_score = severity * proximity * sector
    is_alert    = total_score >= RISK_THRESHOLD

    return {
        **article,
        "severity":     severity,
        "proximity":    proximity,
        "sector":       sector,
        "risk_score":   total_score,
        "is_alert":     is_alert,
    }


def score_all_articles(articles: list[dict]) -> list[dict]:
    """
    Scores all articles and returns them sorted by risk score (highest first).

    Args:
        articles: List of parsed article dicts from news_fetcher

    Returns:
        List of scored articles sorted by risk_score descending
    """
    print(f"\n[RISK SCORER] Scoring {len(articles)} articles (threshold: {RISK_THRESHOLD})...\n")

    scored = [score_article(a) for a in articles]
    scored.sort(key=lambda x: x["risk_score"], reverse=True)

    # Summary stats
    alerts    = [a for a in scored if a["is_alert"]]
    high_risk = [a for a in scored if a["risk_score"] >= 20]

    print(f"  Alerts triggered (score ≥ {RISK_THRESHOLD}) : {len(alerts)}")
    print(f"  High risk (score ≥ 20)                      : {len(high_risk)}")
    print(f"  Total articles scored                        : {len(scored)}")

    return scored


def print_scored_articles(scored_articles: list[dict], top_n: int = 5):
    """Pretty prints the top N scored articles for debugging."""
    print(f"\n{'═'*65}")
    print(f"  TOP {top_n} RISK ARTICLES")
    print(f"{'═'*65}")

    for i, article in enumerate(scored_articles[:top_n], 1):
        alert_tag = " 🚨 ALERT" if article["is_alert"] else ""
        print(f"\n[{i}] Score: {article['risk_score']}/45{alert_tag}")
        print(f"    Title    : {article['title'][:80]}")
        print(f"    Severity : {article['severity']} | "
              f"Proximity: {article['proximity']} | "
              f"Sector: {article['sector']}")
        print(f"    Source   : {article['source']} | {article['published_at'][:10]}")


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Test with mock articles to verify scoring logic
    mock_articles = [
        {
            "title": "Major flood hits Mumbai port, cargo operations suspended",
            "description": "Severe flooding in Maharashtra causes complete shutdown of JNPT operations affecting steel imports",
            "url": "https://example.com/1",
            "source": "Test",
            "published_at": "2026-03-28",
            "content_snippet": "",
        },
        {
            "title": "Truck drivers strike in Punjab disrupts supply chain",
            "description": "Thousands of truck drivers in Ludhiana go on strike affecting textile and steel deliveries",
            "url": "https://example.com/2",
            "source": "Test",
            "published_at": "2026-03-28",
            "content_snippet": "",
        },
        {
            "title": "Global shipping rates see marginal increase",
            "description": "International freight rates show slight uptick due to seasonal demand",
            "url": "https://example.com/3",
            "source": "Test",
            "published_at": "2026-03-28",
            "content_snippet": "",
        },
    ]

    scored = score_all_articles(mock_articles)
    print_scored_articles(scored, top_n=3)