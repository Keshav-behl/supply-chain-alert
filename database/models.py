"""
database/models.py
------------------
Direct PostgreSQL connection to Supabase using SQLAlchemy.
Much more reliable than the Supabase Python client.

Setup:
    1. pip install psycopg2-binary sqlalchemy
    2. Add DATABASE_URL to your .env
    3. Run: python database/models.py
       (prints schema SQL to run in Supabase SQL Editor)
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


# ─────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────

def get_engine():
    """Creates and returns SQLAlchemy engine."""
    if not DATABASE_URL:
        raise EnvironmentError(
            "DATABASE_URL not found in .env.\n"
            "Get it from: supabase.com → Connect → Direct → Connection string"
        )
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def get_session():
    """Returns a SQLAlchemy session."""
    engine  = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# ─────────────────────────────────────────────
# SCHEMA SQL
# ─────────────────────────────────────────────

def get_schema_sql() -> str:
    return """
-- ── Pipeline Runs ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              BIGSERIAL PRIMARY KEY,
    run_at          TIMESTAMPTZ DEFAULT NOW(),
    articles_count  INT         DEFAULT 0,
    max_risk_score  INT         DEFAULT 0,
    alert_count     INT         DEFAULT 0,
    is_anomaly      BOOLEAN     DEFAULT FALSE,
    action_required BOOLEAN     DEFAULT FALSE,
    rfqs_generated  INT         DEFAULT 0,
    summary         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Risk Articles ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_articles (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT      REFERENCES pipeline_runs(id),
    title           TEXT        NOT NULL,
    description     TEXT,
    source          TEXT,
    url             TEXT,
    published_at    TEXT,
    risk_score      INT         DEFAULT 0,
    severity        INT         DEFAULT 0,
    proximity       INT         DEFAULT 0,
    sector          INT         DEFAULT 0,
    is_alert        BOOLEAN     DEFAULT FALSE,
    is_weather      BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Vendor RFQs ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vendor_rfqs (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT      REFERENCES pipeline_runs(id),
    vendor_name     TEXT        NOT NULL,
    vendor_whatsapp TEXT,
    vendor_location TEXT,
    material        TEXT        NOT NULL,
    message_sent    TEXT,
    status          TEXT        DEFAULT 'pending',
    reply_text      TEXT,
    price_per_unit  FLOAT,
    available_qty   FLOAT,
    lead_time_days  INT,
    confidence      TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    replied_at      TIMESTAMPTZ
);

-- ── Indexes ────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_risk_articles_run_id ON risk_articles(run_id);
CREATE INDEX IF NOT EXISTS idx_risk_articles_score  ON risk_articles(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_vendor_rfqs_run_id   ON vendor_rfqs(run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_at ON pipeline_runs(run_at DESC);
"""


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing PostgreSQL connection...\n")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL: {version[:50]}")
            print(f"\n{'─'*60}")
            print("Now run this SQL in Supabase SQL Editor:")
            print("supabase.com → SQL Editor → paste → Run")
            print(f"{'─'*60}")
            print(get_schema_sql())
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nCheck your DATABASE_URL in .env")
        print("Format: postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres")