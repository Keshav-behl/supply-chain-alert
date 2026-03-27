"""
main.py
-------
Entry point for the Supply Chain Disruption Alert Agent.
Run this file to execute one full pipeline cycle manually.

Usage:
    python main.py

For scheduled runs, use the scheduler (coming in Phase 2).
"""

from data_ingestion.news_fetcher import fetch_all_risk_news


def run_pipeline():
    print("\n" + "═"*60)
    print("  SUPPLY CHAIN ALERT AGENT — Pipeline Run")
    print("═"*60)

    # ── Phase 1: Ingest ──────────────────────────────────────
    print("\n[1/5] Fetching risk news...")
    articles = fetch_all_risk_news()
    print(f"      → {len(articles)} articles ingested")

    # ── Phase 2: Score ───────────────────────────────────────
    # Coming next: risk_scorer.py
    print("\n[2/5] Scoring disruption risk...")
    print("      → [Not built yet — coming next session]")

    # ── Phase 3: Anomaly Detection ───────────────────────────
    print("\n[3/5] Running anomaly detection...")
    print("      → [Not built yet]")

    # ── Phase 4: Inventory Check ─────────────────────────────
    print("\n[4/5] Checking inventory buffers...")
    print("      → [Not built yet]")

    # ── Phase 5: Vendor Agent ────────────────────────────────
    print("\n[5/5] Contacting backup vendors if needed...")
    print("      → [Not built yet]")

    print("\n" + "═"*60)
    print("  Pipeline run complete.")
    print("═"*60 + "\n")


if __name__ == "__main__":
    run_pipeline()
