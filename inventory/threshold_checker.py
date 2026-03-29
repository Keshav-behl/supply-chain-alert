"""
threshold_checker.py
--------------------
Cross-references disruption alerts with inventory levels.

The key question it answers:
    "Given this disruption, which of our materials are at risk
     and do we have enough buffer stock to ride it out?"

Logic:
    1. Take the top scored/alerted articles
    2. Extract which materials/sectors they affect
    3. Match against inventory
    4. Flag materials that are both disrupted AND low on stock
    5. Return action items for the vendor agent
"""

# ─────────────────────────────────────────────
# MATERIAL → KEYWORD MAPPING
# ─────────────────────────────────────────────
# Maps inventory material names to news keywords
# If any of these keywords appear in a disruption alert,
# that material is considered "at risk"

MATERIAL_RISK_KEYWORDS = {
    "steel":     ["steel", "iron", "metal", "port", "freight", "cargo"],
    "aluminium": ["aluminium", "aluminum", "metal", "smelter", "power outage"],
    "coal":      ["coal", "coke", "mine", "railway", "freight", "energy"],
    "diesel":    ["diesel", "fuel", "petrol", "crude", "oil", "refinery"],
    "cotton":    ["cotton", "textile", "yarn", "fabric", "flood", "gujarat"],
    "polymer":   ["polymer", "plastic", "resin", "chemical", "crude", "oil"],
    "copper":    ["copper", "metal", "mining", "port", "freight"],
    "cement":    ["cement", "limestone", "clinker", "flood", "highway"],
}

# How many days of disruption to assume when planning buffer
ASSUMED_DISRUPTION_DAYS = 14   # Assume 2 weeks of disruption impact


# ─────────────────────────────────────────────
# RISK MATCHING
# ─────────────────────────────────────────────

def extract_disruption_keywords(scored_articles: list[dict]) -> set[str]:
    """
    Pulls all relevant keywords from alerted articles.
    Returns a flat set of keywords found in disruption news.
    """
    keywords_found = set()

    for article in scored_articles:
        if not article.get("is_alert"):
            continue

        text = (
            (article.get("title") or "") + " " +
            (article.get("description") or "")
        ).lower()

        # Check every material's keywords against article text
        for material, keywords in MATERIAL_RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    keywords_found.add(keyword)

    return keywords_found


def find_at_risk_materials(
    inventory: list[dict],
    scored_articles: list[dict]
) -> list[dict]:
    """
    Matches disruption alerts to inventory materials.

    Returns list of at-risk materials with:
    - Why they're at risk (which keyword triggered)
    - Whether stock is sufficient to weather the disruption
    - Urgency level
    """
    at_risk = []

    for item in inventory:
        material = item["material"]
        keywords = MATERIAL_RISK_KEYWORDS.get(material, [])

        # Check if any alert article mentions this material's keywords
        triggering_articles = []
        for article in scored_articles:
            if not article.get("is_alert"):
                continue

            text = (
                (article.get("title") or "") + " " +
                (article.get("description") or "")
            ).lower()

            for keyword in keywords:
                if keyword in text:
                    triggering_articles.append(article)
                    break

        if not triggering_articles:
            continue  # This material not affected by current disruptions

        # Material IS affected — now check if stock is sufficient
        current_days  = item["current_stock_days"]
        safe_days     = item["minimum_safe_days"]
        buffer_after  = current_days - ASSUMED_DISRUPTION_DAYS

        # Determine urgency
        if current_days < ASSUMED_DISRUPTION_DAYS:
            urgency = "CRITICAL"   # Will run out during disruption
        elif current_days < safe_days:
            urgency = "HIGH"       # Already below safe level
        elif buffer_after < safe_days:
            urgency = "MEDIUM"     # Will drop below safe during disruption
        else:
            urgency = "LOW"        # Enough buffer to ride it out

        at_risk.append({
            **item,
            "urgency":             urgency,
            "buffer_after_days":   buffer_after,
            "assumed_disruption":  ASSUMED_DISRUPTION_DAYS,
            "triggering_headline": triggering_articles[0]["title"][:80],
            "needs_vendor_action": urgency in ("CRITICAL", "HIGH", "MEDIUM"),
        })

    # Sort by urgency (critical first)
    urgency_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    at_risk.sort(key=lambda x: urgency_order[x["urgency"]])

    return at_risk


def run_inventory_check(
    inventory: list[dict],
    scored_articles: list[dict],
    detection: dict
) -> dict:
    """
    Main function. Runs full inventory check against disruption alerts.

    Args:
        inventory:       Loaded inventory from inventory_manager
        scored_articles: Scored articles from risk_scorer
        detection:       Anomaly detection result

    Returns:
        {
            "at_risk_materials":  list of at-risk material dicts,
            "action_required":    bool,
            "critical_count":     int,
            "summary":            str
        }
    """
    print(f"\n[INVENTORY CHECK] Cross-referencing disruptions with stock levels...\n")

    # If no anomaly detected and no alerts, skip deep check
    if not detection.get("should_act") and detection.get("alert_count", 0) == 0:
        print("  No actionable disruptions detected. Inventory check skipped.")
        return {
            "at_risk_materials": [],
            "action_required":   False,
            "critical_count":    0,
            "summary":           "No disruptions requiring inventory review.",
        }

    at_risk = find_at_risk_materials(inventory, scored_articles)

    if not at_risk:
        print("  ✅ No inventory materials affected by current disruptions.")
        return {
            "at_risk_materials": [],
            "action_required":   False,
            "critical_count":    0,
            "summary":           "Disruptions detected but no inventory materials directly affected.",
        }

    # Print results
    needs_action = [m for m in at_risk if m["needs_vendor_action"]]
    critical     = [m for m in at_risk if m["urgency"] == "CRITICAL"]

    print(f"  {'─'*55}")
    print(f"  {'Material':<12} {'Stock':>6} {'After':>6} {'Urgency':>10}")
    print(f"  {'─'*55}")

    for item in at_risk:
        print(
            f"  {item['material'].capitalize():<12} "
            f"{item['current_stock_days']:>5}d "
            f"{item['buffer_after_days']:>5}d "
            f"{item['urgency']:>10}"
        )
        print(f"    ↳ Triggered by: {item['triggering_headline']}")

    print(f"\n  Materials needing vendor action : {len(needs_action)}")
    print(f"  Critical (will run out)         : {len(critical)}")

    summary = (
        f"{len(at_risk)} material(s) at risk. "
        f"{len(needs_action)} need vendor outreach. "
        f"{len(critical)} critical."
    )

    return {
        "at_risk_materials": at_risk,
        "action_required":   len(needs_action) > 0,
        "critical_count":    len(critical),
        "summary":           summary,
    }


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from inventory.inventory_manager import load_inventory

    # Mock alert articles
    mock_articles = [
        {
            "title":       "Fuel shortage hits India as Iran war disrupts crude imports",
            "description": "Diesel and petrol supply chains face severe disruption across Gujarat and Maharashtra",
            "risk_score":  27,
            "is_alert":    True,
            "severity":    3,
            "proximity":   3,
            "sector":      3,
        },
        {
            "title":       "Cotton supply disrupted as floods hit Gujarat textile hubs",
            "description": "Major flooding in Surat affects cotton yarn and fabric supply chains",
            "risk_score":  18,
            "is_alert":    True,
            "severity":    3,
            "proximity":   2,
            "sector":      3,
        },
    ]

    mock_detection = {"should_act": True, "alert_count": 2}

    inventory = load_inventory()
    result    = run_inventory_check(inventory, mock_articles, mock_detection)

    print(f"\n{'═'*55}")
    print(f"  Action required: {result['action_required']}")
    print(f"  Summary: {result['summary']}")