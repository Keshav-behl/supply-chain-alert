"""
main.py
-------
Entry point for the Supply Chain Disruption Alert Agent.
Run this file to execute one full pipeline cycle manually.

Usage:
    python main.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_ingestion.news_fetcher import fetch_all_risk_news
from processing.risk_scorer import score_all_articles, print_scored_articles
from processing.anomaly_detector import run_anomaly_detection
from inventory.inventory_manager import load_inventory
from inventory.threshold_checker import run_inventory_check


def run_pipeline():
    print("\n" + "═"*60)
    print("  SUPPLY CHAIN ALERT AGENT — Pipeline Run")
    print("═"*60)

    # ── Phase 1: Ingest ──────────────────────────────────────
    print("\n[1/5] Fetching risk news...")
    articles = fetch_all_risk_news()
    print(f"      → {len(articles)} articles ingested")

    # ── Phase 2: Score ───────────────────────────────────────
    print("\n[2/5] Scoring disruption risk...")
    scored_articles = score_all_articles(articles)
    print_scored_articles(scored_articles, top_n=5)

    # ── Phase 3: Anomaly Detection ───────────────────────────
    print("\n[3/5] Running anomaly detection...")
    detection = run_anomaly_detection(scored_articles)
    print(f"      → Should act: {detection['should_act']}")

    # ── Phase 4: Inventory Check ─────────────────────────────
    print("\n[4/5] Checking inventory buffers...")
    inventory = load_inventory()
    inventory_result = run_inventory_check(inventory, scored_articles, detection)
    print(f"      → {inventory_result['summary']}")

    # ── Phase 5: Vendor Agent ────────────────────────────────
    print("\n[5/5] Contacting backup vendors if needed...")
    if inventory_result["action_required"]:
        print("      → Action required — vendor agent coming next build")
    else:
        print("      → No vendor action needed right now")

    print("\n" + "═"*60)
    print("  Pipeline run complete.")
    print("═"*60 + "\n")


if __name__ == "__main__":
    run_pipeline()