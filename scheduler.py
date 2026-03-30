"""
scheduler.py
------------
Runs the full supply chain pipeline automatically every 6 hours.
Uses APScheduler — lightweight, no external dependencies needed.

Usage:
    python scheduler.py

Keep this running on your machine or deploy to Railway/Render.
The pipeline runs at: 06:00, 12:00, 18:00, 00:00 UTC daily.

Ctrl+C to stop.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import logging
from datetime import datetime, UTC
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Import pipeline
from main import run_pipeline

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),                          # Console
        logging.FileHandler("scheduler.log"),             # File
    ]
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# SCHEDULED JOB
# ─────────────────────────────────────────────

def scheduled_pipeline_run():
    """Wrapper around run_pipeline with error handling and logging."""
    run_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    log.info(f"Scheduled pipeline run starting — {run_time}")

    try:
        run_pipeline()
        log.info(f"Pipeline run completed successfully")

    except Exception as e:
        log.error(f"Pipeline run failed: {type(e).__name__}: {e}")
        # Don't crash the scheduler — just log and continue


# ─────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────

def start_scheduler():
    """
    Starts the APScheduler with a 6-hour cron trigger.
    Runs at 06:00, 12:00, 18:00, 00:00 UTC.
    Also runs once immediately on startup.
    """
    scheduler = BlockingScheduler(timezone="UTC")

    # Schedule every 6 hours
    scheduler.add_job(
        func=scheduled_pipeline_run,
        trigger=CronTrigger(hour="0,6,12,18", minute=0),
        id="supply_chain_pipeline",
        name="Supply Chain Disruption Pipeline",
        misfire_grace_time=300,    # Allow 5 min late start
        coalesce=True,             # Don't stack missed runs
    )

    print("\n" + "═"*60)
    print("  SUPPLY CHAIN ALERT — SCHEDULER STARTED")
    print("═"*60)
    print(f"  Runs at  : 00:00, 06:00, 12:00, 18:00 UTC")
    print(f"  Started  : {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Log file : scheduler.log")
    print(f"  Stop     : Ctrl+C")
    print("═"*60 + "\n")

    log.info("Scheduler started — running immediately then every 6 hours")

    # Run once immediately on startup
    print("[SCHEDULER] Running pipeline immediately on startup...\n")
    scheduled_pipeline_run()

    # Then start the scheduler for subsequent runs
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Stopped by user.")
        log.info("Scheduler stopped by user")
        scheduler.shutdown()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    start_scheduler()