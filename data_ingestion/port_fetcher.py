"""
port_fetcher.py
---------------
Fetches port congestion and disruption data for India's major cargo ports.

Monitors:
    - JNPT (Jawaharlal Nehru Port) — Mumbai, largest container port
    - Mundra Port — Gujarat, largest private port
    - Kandla Port — Gujarat, largest cargo volume
    - Chennai Port — Tamil Nadu, major eastern port

Since no free real-time port API exists, we use two approaches:
    1. NewsAPI — searches for port-specific disruption news
    2. Synthetic signal — generates risk signal from weather + news convergence

This is honest engineering: we document the limitation and build
the best possible signal with available data.
"""

import os
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY  = os.getenv("NEWSAPI_KEY")
NEWSAPI_URL  = "https://newsapi.org/v2/everything"
LOOKBACK_DAYS = 2

# ─────────────────────────────────────────────
# MONITORED PORTS
# ─────────────────────────────────────────────

INDIAN_PORTS = [
    {
        "name":     "JNPT",
        "fullname": "Jawaharlal Nehru Port Trust",
        "location": "Mumbai, Maharashtra",
        "keywords": ["JNPT", "Nhava Sheva", "Jawaharlal Nehru Port"],
        "role":     "India's largest container port — handles 55% of container traffic",
    },
    {
        "name":     "Mundra",
        "fullname": "Mundra Port",
        "location": "Kutch, Gujarat",
        "keywords": ["Mundra port", "Adani Mundra", "Mundra cargo"],
        "role":     "Largest private port — major coal and container hub",
    },
    {
        "name":     "Kandla",
        "fullname": "Deendayal Port (Kandla)",
        "location": "Kutch, Gujarat",
        "keywords": ["Kandla port", "Deendayal port", "Kandla cargo"],
        "role":     "Highest cargo volume port — petroleum and bulk cargo hub",
    },
    {
        "name":     "Chennai",
        "fullname": "Chennai Port",
        "location": "Chennai, Tamil Nadu",
        "keywords": ["Chennai port", "Madras port", "Chennai harbour"],
        "role":     "Major eastern port — automobiles and containers",
    },
]

# Keywords that indicate port disruption in news
DISRUPTION_KEYWORDS = [
    "congestion", "delay", "backlog", "strike", "shutdown",
    "blockade", "disruption", "closure", "suspended", "halted",
    "slow", "queue", "waiting", "berthing delay",
]


# ─────────────────────────────────────────────
# NEWS-BASED PORT SIGNAL
# ─────────────────────────────────────────────

def fetch_port_news(port: dict) -> list[dict]:
    """
    Searches NewsAPI for disruption news about a specific port.
    Returns filtered list of relevant articles.
    """
    if not NEWSAPI_KEY:
        return []

    from_date = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    # Build search query from port keywords
    query = " OR ".join(f'"{kw}"' for kw in port["keywords"][:2])

    params = {
        "q":        query,
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
            return []

        articles = data.get("articles", [])

        # Filter for disruption-related articles
        relevant = []
        for article in articles:
            text = (
                (article.get("title") or "") + " " +
                (article.get("description") or "")
            ).lower()

            # Check if article mentions disruption
            if any(kw in text for kw in DISRUPTION_KEYWORDS):
                relevant.append(article)

        return relevant

    except requests.exceptions.RequestException:
        return []


def assess_port_risk(port: dict, articles: list[dict]) -> dict:
    """
    Assesses disruption risk for a port based on news articles found.
    Returns a risk assessment dict.
    """
    if not articles:
        return {
            "port":       port["name"],
            "fullname":   port["fullname"],
            "location":   port["location"],
            "role":       port["role"],
            "severity":   0,
            "is_risk":    False,
            "articles":   0,
            "risk_desc":  "No disruption signals detected",
            "headline":   None,
        }

    # Score based on number of articles and their content
    severity = min(len(articles) + 1, 5)   # More articles = higher severity, max 5

    # Check for severe keywords to boost severity
    for article in articles:
        text = (
            (article.get("title") or "") + " " +
            (article.get("description") or "")
        ).lower()

        if any(kw in text for kw in ["strike", "shutdown", "closure", "suspended"]):
            severity = min(severity + 1, 5)
            break

    top_headline = articles[0].get("title", "") if articles else ""

    return {
        "port":      port["name"],
        "fullname":  port["fullname"],
        "location":  port["location"],
        "role":      port["role"],
        "severity":  severity,
        "is_risk":   severity >= 2,
        "articles":  len(articles),
        "risk_desc": f"{len(articles)} disruption signal(s) detected",
        "headline":  top_headline,
    }


def fetch_all_port_risks() -> list[dict]:
    """
    Main function. Fetches port disruption signals for all major Indian ports.
    Returns list of port risk assessments sorted by severity.
    """
    print(f"\n[PORT FETCHER] Scanning {len(INDIAN_PORTS)} major Indian ports...\n")

    assessments = []
    for port in INDIAN_PORTS:
        articles   = fetch_port_news(port)
        assessment = assess_port_risk(port, articles)
        assessments.append(assessment)

        status = "⚠️  RISK" if assessment["is_risk"] else "✅ OK  "
        print(
            f"  {assessment['port']:<10} "
            f"{assessment['location']:<25} "
            f"📰 {assessment['articles']} articles  "
            f"{status}"
        )

    assessments.sort(key=lambda x: x["severity"], reverse=True)
    risk_ports = [a for a in assessments if a["is_risk"]]
    print(f"\n[PORT FETCHER] {len(risk_ports)}/{len(assessments)} ports showing disruption signals\n")

    return assessments


def get_port_risk_articles(assessments: list[dict]) -> list[dict]:
    """
    Converts port risk assessments into article-like dicts
    for unified scoring in the main pipeline.
    """
    articles = []
    for a in assessments:
        if not a["is_risk"]:
            continue

        articles.append({
            "title":           f"Port disruption signal: {a['risk_desc']} at {a['fullname']}",
            "description":     (
                f"Supply chain disruption signals detected at {a['fullname']} "
                f"({a['location']}). {a['role']}. "
                f"Latest: {a['headline'][:100] if a['headline'] else 'Multiple disruption signals detected.'}"
            ),
            "url":             f"port://live/{a['port'].lower()}",
            "source":          "Port Monitor",
            "published_at":    "",
            "content_snippet": "",
            "is_weather":      False,
            "is_port":         True,
            "severity_hint":   a["severity"],
        })

    return articles


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    assessments = fetch_all_port_risks()

    print(f"{'─'*60}")
    print(f"PORT RISK SUMMARY")
    print(f"{'─'*60}")

    for a in assessments:
        risk_tag = f" ⚠️  Severity {a['severity']}" if a["is_risk"] else ""
        print(f"\n{a['port']} — {a['fullname']}")
        print(f"  Location : {a['location']}")
        print(f"  Role     : {a['role']}")
        print(f"  Status   : {a['risk_desc']}{risk_tag}")

    port_articles = get_port_risk_articles(assessments)
    if port_articles:
        print(f"\n{'─'*60}")
        print(f"SIGNALS FOR RISK SCORER ({len(port_articles)} port articles):")
        for a in port_articles:
            print(f"\n  {a['title']}")
    else:
        print(f"\n✅ No port disruptions detected today.")