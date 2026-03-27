"""
anomaly_detector.py
-------------------
Detects whether current risk scores are unusually high
compared to recent historical patterns.

Why this matters:
    Without anomaly detection, the system alerts on EVERY
    disruption above the threshold — even normal background noise.
    This layer asks: "Is today's risk score unusual vs the past 30 days?"
    Only truly abnormal spikes trigger the full vendor agent.

Approach:
    - Maintains a rolling window of daily risk scores in a JSON file
    - Uses Z-score to detect statistical outliers
    - Falls back to simple threshold if not enough history yet
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

HISTORY_FILE      = "risk_score_history.json"   # Local file to store history
WINDOW_DAYS       = 30                           # How many days of history to keep
ZSCORE_THRESHOLD  = 1.5                          # Flag if score is 1.5 std devs above mean
MIN_HISTORY_DAYS  = 5                            # Min days needed before using Z-score
RISK_THRESHOLD    = int(os.getenv("RISK_SCORE_THRESHOLD", 25))


# ─────────────────────────────────────────────
# HISTORY MANAGEMENT
# ─────────────────────────────────────────────

def load_history() -> list[dict]:
    """
    Loads risk score history from local JSON file.
    Returns empty list if file doesn't exist yet.
    """
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_history(history: list[dict]):
    """Saves risk score history to local JSON file."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except IOError as e:
        print(f"  [WARN] Could not save history: {e}")


def prune_old_history(history: list[dict]) -> list[dict]:
    """
    Removes entries older than WINDOW_DAYS.
    Keeps the rolling window lean.
    """
    cutoff = datetime.utcnow() - timedelta(days=WINDOW_DAYS)
    return [
        entry for entry in history
        if datetime.fromisoformat(entry["date"]) >= cutoff
    ]


def add_to_history(history: list[dict], date: str, max_score: int, alert_count: int) -> list[dict]:
    """
    Adds today's risk summary to history.
    Replaces existing entry for today if already present.
    """
    # Remove today's entry if it exists (avoid duplicates on re-runs)
    history = [e for e in history if e["date"] != date]

    history.append({
        "date":        date,
        "max_score":   max_score,
        "alert_count": alert_count,
    })

    return history


# ─────────────────────────────────────────────
# ANOMALY DETECTION
# ─────────────────────────────────────────────

def compute_zscore(current_score: float, historical_scores: list[float]) -> float:
    """
    Computes Z-score: how many standard deviations above the mean.
    Z = (current - mean) / std_dev
    """
    if len(historical_scores) < 2:
        return 0.0

    mean    = np.mean(historical_scores)
    std_dev = np.std(historical_scores)

    if std_dev == 0:
        return 0.0

    return (current_score - mean) / std_dev


def is_anomaly(current_score: int, history: list[dict]) -> tuple[bool, str]:
    """
    Determines if the current risk score is anomalous.

    Returns:
        (is_anomalous: bool, reason: str)

    Logic:
        - If history < MIN_HISTORY_DAYS: fall back to simple threshold
        - Otherwise: use Z-score detection
    """
    historical_scores = [entry["max_score"] for entry in history]

    # ── Not enough history yet ───────────────────────────────
    if len(historical_scores) < MIN_HISTORY_DAYS:
        days_remaining = MIN_HISTORY_DAYS - len(historical_scores)
        reason = (
            f"Insufficient history ({len(historical_scores)}/{MIN_HISTORY_DAYS} days). "
            f"Using threshold fallback. {days_remaining} more days needed for Z-score."
        )
        return current_score >= RISK_THRESHOLD, reason

    # ── Z-score detection ────────────────────────────────────
    zscore = compute_zscore(current_score, historical_scores)
    mean   = np.mean(historical_scores)
    std    = np.std(historical_scores)

    if zscore >= ZSCORE_THRESHOLD:
        reason = (
            f"ANOMALY DETECTED — Z-score: {zscore:.2f} "
            f"(mean: {mean:.1f}, std: {std:.1f}, current: {current_score}). "
            f"Score is {zscore:.1f} standard deviations above normal."
        )
        return True, reason
    else:
        reason = (
            f"Normal range — Z-score: {zscore:.2f} "
            f"(mean: {mean:.1f}, std: {std:.1f}, current: {current_score}). "
            f"No anomaly detected."
        )
        return False, reason


# ─────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────

def run_anomaly_detection(scored_articles: list[dict]) -> dict:
    """
    Main function. Takes scored articles, checks for anomalies,
    updates history, and returns detection result.

    Args:
        scored_articles: List of scored article dicts from risk_scorer

    Returns:
        {
            "is_anomaly":    bool,
            "reason":        str,
            "max_score":     int,
            "alert_count":   int,
            "history_days":  int,
            "should_act":    bool   ← True if vendor agent should run
        }
    """
    print(f"\n[ANOMALY DETECTOR] Analysing risk pattern...\n")

    # Extract today's metrics from scored articles
    if not scored_articles:
        print("  [WARN] No scored articles provided.")
        return {
            "is_anomaly":   False,
            "reason":       "No articles to analyse.",
            "max_score":    0,
            "alert_count":  0,
            "history_days": 0,
            "should_act":   False,
        }

    max_score   = scored_articles[0]["risk_score"]   # Already sorted desc
    alert_count = sum(1 for a in scored_articles if a["is_alert"])
    today       = datetime.utcnow().strftime("%Y-%m-%d")

    # Load and update history
    history = load_history()
    history = prune_old_history(history)

    # Check anomaly BEFORE adding today (compare against past only)
    anomaly_detected, reason = is_anomaly(max_score, history)

    # Now add today to history and save
    history = add_to_history(history, today, max_score, alert_count)
    save_history(history)

    # Print results
    status = "🚨 ANOMALY" if anomaly_detected else "✅ NORMAL"
    print(f"  Status       : {status}")
    print(f"  Today score  : {max_score}/45")
    print(f"  Alert count  : {alert_count}")
    print(f"  History days : {len(history)}")
    print(f"  Reason       : {reason}")

    return {
        "is_anomaly":   anomaly_detected,
        "reason":       reason,
        "max_score":    max_score,
        "alert_count":  alert_count,
        "history_days": len(history),
        "should_act":   anomaly_detected and alert_count > 0,
    }


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Simulate 6 days of history then test an anomaly
    print("Seeding mock history for testing...\n")

    mock_history = []
    base_date = datetime.utcnow() - timedelta(days=6)

    # Normal days — scores between 8 and 15
    for i in range(6):
        date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        mock_history.append({
            "date":        date,
            "max_score":   10 + i,
            "alert_count": 0,
        })

    save_history(mock_history)
    print(f"Seeded {len(mock_history)} days of history (scores 10–15)\n")

    # Now simulate today with a spike
    mock_scored = [
        {
            "title":      "Major flood hits Mumbai port, steel imports suspended",
            "risk_score": 27,
            "is_alert":   True,
            "severity":   3,
            "proximity":  3,
            "sector":     3,
        }
    ]

    result = run_anomaly_detection(mock_scored)

    print(f"\n{'─'*50}")
    print(f"Should vendor agent run? → {result['should_act']}")