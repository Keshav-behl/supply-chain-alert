"""
database/crud.py
----------------
Read/write functions using direct PostgreSQL via SQLAlchemy.
"""

from datetime import datetime, UTC
from sqlalchemy import text
from database.models import get_engine


# ─────────────────────────────────────────────
# PIPELINE RUNS
# ─────────────────────────────────────────────

def save_pipeline_run(
    articles_count:  int,
    max_risk_score:  int,
    alert_count:     int,
    is_anomaly:      bool,
    action_required: bool,
    rfqs_generated:  int,
    summary:         str,
) -> int | None:
    """Saves a pipeline run and returns its run_id."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO pipeline_runs
                    (run_at, articles_count, max_risk_score, alert_count,
                     is_anomaly, action_required, rfqs_generated, summary)
                VALUES
                    (:run_at, :articles_count, :max_risk_score, :alert_count,
                     :is_anomaly, :action_required, :rfqs_generated, :summary)
                RETURNING id
            """), {
                "run_at":          datetime.now(UTC).isoformat(),
                "articles_count":  articles_count,
                "max_risk_score":  max_risk_score,
                "alert_count":     alert_count,
                "is_anomaly":      is_anomaly,
                "action_required": action_required,
                "rfqs_generated":  rfqs_generated,
                "summary":         summary,
            })
            conn.commit()
            run_id = result.fetchone()[0]
            print(f"  [DB] Pipeline run saved → run_id: {run_id}")
            return run_id

    except Exception as e:
        print(f"  [DB WARN] Failed to save pipeline run: {e}")
        return None


def get_recent_pipeline_runs(limit: int = 30) -> list[dict]:
    """Returns most recent pipeline runs for dashboard."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM pipeline_runs
                ORDER BY run_at DESC
                LIMIT :limit
            """), {"limit": limit})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
    except Exception as e:
        print(f"  [DB WARN] Failed to fetch pipeline runs: {e}")
        return []


# ─────────────────────────────────────────────
# RISK ARTICLES
# ─────────────────────────────────────────────

def save_risk_articles(run_id: int, articles: list[dict]) -> bool:
    """Saves all scored articles for a pipeline run."""
    if not run_id or not articles:
        return False

    rows = [
        {
            "run_id":       run_id,
            "title":        (a.get("title") or "")[:500],
            "description":  (a.get("description") or "")[:1000],
            "source":       (a.get("source") or "")[:100],
            "url":          (a.get("url") or "")[:500],
            "published_at": (a.get("published_at") or "")[:50],
            "risk_score":   a.get("risk_score", 0),
            "severity":     a.get("severity", 0),
            "proximity":    a.get("proximity", 0),
            "sector":       a.get("sector", 0),
            "is_alert":     a.get("is_alert", False),
            "is_weather":   a.get("is_weather", False),
        }
        for a in articles if a.get("risk_score", 0) > 0
    ]

    if not rows:
        return False

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO risk_articles
                    (run_id, title, description, source, url, published_at,
                     risk_score, severity, proximity, sector, is_alert, is_weather)
                VALUES
                    (:run_id, :title, :description, :source, :url, :published_at,
                     :risk_score, :severity, :proximity, :sector, :is_alert, :is_weather)
            """), rows)
            conn.commit()
        print(f"  [DB] {len(rows)} articles saved for run_id: {run_id}")
        return True

    except Exception as e:
        print(f"  [DB WARN] Failed to save articles: {e}")
        return False


def get_top_articles(limit: int = 20) -> list[dict]:
    """Returns highest scoring articles across all runs."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM risk_articles
                ORDER BY risk_score DESC
                LIMIT :limit
            """), {"limit": limit})
            return [dict(row._mapping) for row in result.fetchall()]
    except Exception as e:
        print(f"  [DB WARN] Failed to fetch articles: {e}")
        return []


# ─────────────────────────────────────────────
# VENDOR RFQS
# ─────────────────────────────────────────────

def save_vendor_rfqs(run_id: int, rfqs: list[dict]) -> bool:
    """Saves all generated RFQs for a pipeline run."""
    if not run_id or not rfqs:
        return False

    rows = [
        {
            "run_id":          run_id,
            "vendor_name":     (r.get("name") or "")[:200],
            "vendor_whatsapp": (r.get("whatsapp") or "")[:50],
            "vendor_location": (r.get("location") or "")[:200],
            "material":        (r.get("material") or "")[:100],
            "message_sent":    (r.get("message") or "")[:2000],
            "status":          r.get("status", "pending"),
        }
        for r in rfqs
    ]

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO vendor_rfqs
                    (run_id, vendor_name, vendor_whatsapp, vendor_location,
                     material, message_sent, status)
                VALUES
                    (:run_id, :vendor_name, :vendor_whatsapp, :vendor_location,
                     :material, :message_sent, :status)
            """), rows)
            conn.commit()
        print(f"  [DB] {len(rows)} RFQs saved for run_id: {run_id}")
        return True

    except Exception as e:
        print(f"  [DB WARN] Failed to save RFQs: {e}")
        return False


def get_rfq_history(limit: int = 50) -> list[dict]:
    """Returns recent RFQ history for dashboard."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM vendor_rfqs
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})
            return [dict(row._mapping) for row in result.fetchall()]
    except Exception as e:
        print(f"  [DB WARN] Failed to fetch RFQ history: {e}")
        return []


# ─────────────────────────────────────────────
# CONVENIENCE
# ─────────────────────────────────────────────

def save_full_pipeline_run(
    scored_articles:  list[dict],
    detection:        dict,
    inventory_result: dict,
    rfqs:             list[dict],
) -> int | None:
    """Saves everything from one pipeline run in correct order."""
    print(f"\n[DATABASE] Saving pipeline run to Supabase...")

    alerts    = [a for a in scored_articles if a.get("is_alert")]
    max_score = scored_articles[0]["risk_score"] if scored_articles else 0

    run_id = save_pipeline_run(
        articles_count=  len(scored_articles),
        max_risk_score=  max_score,
        alert_count=     len(alerts),
        is_anomaly=      detection.get("is_anomaly", False),
        action_required= inventory_result.get("action_required", False),
        rfqs_generated=  len(rfqs),
        summary=         inventory_result.get("summary", ""),
    )

    if not run_id:
        return None

    save_risk_articles(run_id, scored_articles)
    save_vendor_rfqs(run_id, rfqs)

    print(f"  [DB] ✅ Full run saved → run_id: {run_id}")
    return run_id


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing CRUD...\n")

    run_id = save_pipeline_run(
        articles_count=  17,
        max_risk_score=  30,
        alert_count=     2,
        is_anomaly=      True,
        action_required= True,
        rfqs_generated=  9,
        summary=         "Test run — DB integration check",
    )

    if run_id:
        print(f"\n✅ Test run saved — run_id: {run_id}")
        runs = get_recent_pipeline_runs(limit=3)
        print(f"✅ Fetched {len(runs)} recent runs")
        for r in runs:
            print(f"   id:{r['id']} score:{r['max_risk_score']} {str(r['run_at'])[:10]}")
    else:
        print("❌ DB save failed — check DATABASE_URL in .env")