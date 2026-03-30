"""
main.py
-------
Entry point for the Supply Chain Disruption Alert Agent.
Run this file manually or let scheduler.py run it every 6 hours.

Usage:
    python main.py          # Single run
    python scheduler.py     # Automated every 6 hours
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_ingestion.news_fetcher    import fetch_all_risk_news
from data_ingestion.weather_fetcher import fetch_all_weather_risks, get_weather_risk_articles
from data_ingestion.port_fetcher    import fetch_all_port_risks, get_port_risk_articles
from processing.risk_scorer         import score_all_articles, print_scored_articles
from processing.anomaly_detector    import run_anomaly_detection
from inventory.inventory_manager    import load_inventory
from inventory.threshold_checker    import run_inventory_check
from vendor_network.vendor_registry import load_vendor_registry, get_top_vendors
from vendor_network.rfq_generator   import generate_rfqs_for_material
from whatsapp_agent.outbound_rfq    import run_vendor_outreach
from database.crud                  import save_full_pipeline_run

DRY_RUN = True


def run_pipeline():
    print("\n" + "═"*60)
    print("  SUPPLY CHAIN ALERT AGENT — Pipeline Run")
    print("═"*60)

    # ── Phase 1: Ingest ──────────────────────────────────────
    print("\n[1/5] Fetching risk data...")

    articles            = fetch_all_risk_news()
    weather_assessments = fetch_all_weather_risks()
    weather_articles    = get_weather_risk_articles(weather_assessments)
    port_assessments    = fetch_all_port_risks()
    port_articles       = get_port_risk_articles(port_assessments)

    all_articles = articles + weather_articles + port_articles
    print(
        f"      → {len(articles)} news "
        f"+ {len(weather_articles)} weather "
        f"+ {len(port_articles)} port "
        f"= {len(all_articles)} total signals"
    )

    # ── Phase 2: Score ───────────────────────────────────────
    print("\n[2/5] Scoring disruption risk...")
    scored_articles = score_all_articles(all_articles)
    print_scored_articles(scored_articles, top_n=5)

    # ── Phase 3: Anomaly Detection ───────────────────────────
    print("\n[3/5] Running anomaly detection...")
    detection = run_anomaly_detection(scored_articles)
    print(f"      → Should act: {detection['should_act']}")

    # ── Phase 4: Inventory Check ─────────────────────────────
    print("\n[4/5] Checking inventory buffers...")
    inventory        = load_inventory()
    inventory_result = run_inventory_check(inventory, scored_articles, detection)
    print(f"      → {inventory_result['summary']}")

    # ── Phase 5: Vendor Agent ────────────────────────────────
    print("\n[5/5] Running vendor agent...")
    all_rfqs = []

    if not inventory_result["action_required"]:
        print("      → No vendor action needed right now")
    else:
        registry         = load_vendor_registry()
        action_materials = [
            m for m in inventory_result["at_risk_materials"]
            if m["needs_vendor_action"]
        ]

        for material in action_materials:
            vendors = get_top_vendors(registry, material["material"], top_n=3)
            if not vendors:
                continue
            rfqs = generate_rfqs_for_material(
                vendors=vendors,
                material=material,
                disruption_headline=material.get("triggering_headline", "Supply disruption"),
            )
            all_rfqs.extend(rfqs)

        run_vendor_outreach(
            at_risk_materials=action_materials,
            rfqs=all_rfqs,
            dry_run=DRY_RUN,
        )
        print(f"\n      → {len(all_rfqs)} RFQs for {len(action_materials)} materials")

    # ── Save to Database ─────────────────────────────────────
    save_full_pipeline_run(
        scored_articles=  scored_articles,
        detection=        detection,
        inventory_result= inventory_result,
        rfqs=             all_rfqs,
    )

    print("\n" + "═"*60)
    print("  Pipeline run complete.")
    print("═"*60 + "\n")


if __name__ == "__main__":
    run_pipeline()