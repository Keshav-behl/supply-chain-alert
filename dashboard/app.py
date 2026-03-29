"""
dashboard/app.py
----------------
Streamlit dashboard for the Supply Chain Disruption Alert Agent.
Run with: streamlit run dashboard/app.py

Shows live risk scores, inventory status, and RFQ previews.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, UTC
import json

from data_ingestion.news_fetcher import fetch_all_risk_news
from processing.risk_scorer import score_all_articles
from processing.anomaly_detector import run_anomaly_detection, load_history
from inventory.inventory_manager import load_inventory, print_inventory_summary
from inventory.threshold_checker import run_inventory_check
from vendor_network.vendor_registry import load_vendor_registry, get_top_vendors
from vendor_network.rfq_generator import generate_rfqs_for_material


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Supply Chain Alert Agent",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    .stApp {
        background: #0a0e1a;
        color: #e2e8f0;
    }

    .metric-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }

    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.5rem;
        font-weight: 600;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 6px;
    }

    .alert-critical { color: #ef4444; }
    .alert-high     { color: #f97316; }
    .alert-medium   { color: #eab308; }
    .alert-ok       { color: #22c55e; }
    .alert-anomaly  { color: #ef4444; }
    .alert-normal   { color: #22c55e; }

    .article-card {
        background: #111827;
        border-left: 3px solid #334155;
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }

    .article-card.alert {
        border-left-color: #ef4444;
    }

    .article-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 4px;
    }

    .article-meta {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: #64748b;
    }

    .score-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        background: #1e293b;
        color: #94a3b8;
    }

    .score-badge.alert {
        background: #450a0a;
        color: #ef4444;
    }

    .rfq-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.82rem;
        line-height: 1.6;
        color: #cbd5e1;
        white-space: pre-wrap;
    }

    .vendor-name {
        font-size: 0.78rem;
        color: #64748b;
        margin-bottom: 8px;
        font-family: 'IBM Plex Mono', monospace;
    }

    .stButton > button {
        background: #0f172a;
        color: #e2e8f0;
        border: 1px solid #334155;
        border-radius: 6px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        padding: 8px 20px;
        width: 100%;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
    }

    .section-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: #334155;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 16px;
    }

    div[data-testid="stSidebar"] {
        background: #060b14;
        border-right: 1px solid #1e293b;
    }

    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 0;
        font-size: 0.82rem;
        color: #94a3b8;
        font-family: 'IBM Plex Mono', monospace;
    }

    .pipeline-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #334155;
        flex-shrink: 0;
    }

    .pipeline-dot.done  { background: #22c55e; }
    .pipeline-dot.running { background: #3b82f6; animation: pulse 1s infinite; }
    .pipeline-dot.alert { background: #ef4444; }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    .timestamp {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🏭 Supply Chain Agent")
    st.markdown(
        '<div class="timestamp">' +
        datetime.now(UTC).strftime("Last updated: %d %b %Y %H:%M UTC") +
        '</div>',
        unsafe_allow_html=True
    )
    st.divider()

    run_pipeline = st.button("▶ Run Pipeline Now", use_container_width=True)
    st.markdown(" ")

    st.markdown('<div class="section-header">Pipeline Status</div>', unsafe_allow_html=True)

    # Pipeline steps shown in sidebar
    steps = [
        ("News Fetcher",       "done"),
        ("Risk Scorer",        "done"),
        ("Anomaly Detector",   "done"),
        ("Inventory Check",    "done"),
        ("Vendor Agent",       "done"),
    ]

    for step, status in steps:
        dot_class = f"pipeline-dot {status}"
        st.markdown(
            f'<div class="pipeline-step">'
            f'<div class="{dot_class}"></div>{step}'
            f'</div>',
            unsafe_allow_html=True
        )

    st.divider()
    st.markdown('<div class="section-header">Config</div>', unsafe_allow_html=True)
    risk_threshold = st.slider("Alert Threshold", 10, 45, 25)
    lookback_days  = st.slider("Lookback Days", 1, 7, 2)
    top_vendors    = st.slider("Vendors per Material", 1, 3, 3)


# ─────────────────────────────────────────────
# SESSION STATE — cache pipeline results
# ─────────────────────────────────────────────

if "pipeline_ran"       not in st.session_state: st.session_state.pipeline_ran       = False
if "articles"           not in st.session_state: st.session_state.articles           = []
if "scored_articles"    not in st.session_state: st.session_state.scored_articles    = []
if "detection"          not in st.session_state: st.session_state.detection          = {}
if "inventory"          not in st.session_state: st.session_state.inventory          = []
if "inventory_result"   not in st.session_state: st.session_state.inventory_result   = {}
if "rfqs"               not in st.session_state: st.session_state.rfqs               = []


# ─────────────────────────────────────────────
# RUN PIPELINE
# ─────────────────────────────────────────────

if run_pipeline:
    with st.spinner("Running pipeline..."):

        # Phase 1
        articles = fetch_all_risk_news()
        st.session_state.articles = articles

        # Phase 2
        scored = score_all_articles(articles)
        st.session_state.scored_articles = scored

        # Phase 3
        detection = run_anomaly_detection(scored)
        st.session_state.detection = detection

        # Phase 4
        inventory = load_inventory()
        inv_result = run_inventory_check(inventory, scored, detection)
        st.session_state.inventory        = inventory
        st.session_state.inventory_result = inv_result

        # Phase 5 — generate RFQs for action materials
        registry = load_vendor_registry()
        all_rfqs = []
        for material in inv_result.get("at_risk_materials", []):
            if material["needs_vendor_action"]:
                vendors = get_top_vendors(registry, material["material"], top_n=top_vendors)
                if vendors:
                    rfqs = generate_rfqs_for_material(
                        vendors=vendors,
                        material=material,
                        disruption_headline=material.get("triggering_headline", "Supply disruption"),
                    )
                    all_rfqs.extend(rfqs)

        st.session_state.rfqs         = all_rfqs
        st.session_state.pipeline_ran = True

    st.success(f"Pipeline complete — {len(articles)} articles processed")


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown("## Supply Chain Disruption Alert Agent")
st.markdown(
    '<div class="timestamp">Autonomous procurement protection for Indian SME manufacturers</div>',
    unsafe_allow_html=True
)
st.markdown(" ")


# ─────────────────────────────────────────────
# TOP METRICS ROW
# ─────────────────────────────────────────────

detection       = st.session_state.detection
inventory_result = st.session_state.inventory_result
scored_articles = st.session_state.scored_articles

max_score    = detection.get("max_score",    0)
alert_count  = detection.get("alert_count",  0)
is_anomaly   = detection.get("is_anomaly",   False)
at_risk      = len(inventory_result.get("at_risk_materials", []))
action_mats  = sum(1 for m in inventory_result.get("at_risk_materials", []) if m.get("needs_vendor_action"))
rfq_count    = len(st.session_state.rfqs)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    color = "alert-critical" if max_score >= 35 else "alert-high" if max_score >= 25 else "alert-ok"
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value {color}">{max_score}<span style="font-size:1rem">/45</span></div>'
        f'<div class="metric-label">Peak Risk Score</div>'
        f'</div>', unsafe_allow_html=True
    )

with col2:
    color = "alert-critical" if alert_count > 3 else "alert-high" if alert_count > 0 else "alert-ok"
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value {color}">{alert_count}</div>'
        f'<div class="metric-label">Alerts Triggered</div>'
        f'</div>', unsafe_allow_html=True
    )

with col3:
    status_text  = "ANOMALY" if is_anomaly else "NORMAL"
    status_color = "alert-anomaly" if is_anomaly else "alert-normal"
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value {status_color}" style="font-size:1.4rem">{status_text}</div>'
        f'<div class="metric-label">Risk Pattern</div>'
        f'</div>', unsafe_allow_html=True
    )

with col4:
    color = "alert-high" if action_mats > 0 else "alert-ok"
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value {color}">{action_mats}</div>'
        f'<div class="metric-label">Materials at Risk</div>'
        f'</div>', unsafe_allow_html=True
    )

with col5:
    color = "alert-high" if rfq_count > 0 else "alert-ok"
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-value {color}">{rfq_count}</div>'
        f'<div class="metric-label">RFQs Generated</div>'
        f'</div>', unsafe_allow_html=True
    )

st.markdown(" ")


# ─────────────────────────────────────────────
# TWO COLUMN LAYOUT
# ─────────────────────────────────────────────

left, right = st.columns([1.2, 1], gap="large")


# ── LEFT: Risk Articles + Chart ──────────────
with left:

    st.markdown('<div class="section-header">// Risk Scored Articles</div>', unsafe_allow_html=True)

    if scored_articles:
        # Bar chart of top article scores
        top10 = scored_articles[:10]
        titles = [a["title"][:40] + "..." for a in top10]
        scores = [a["risk_score"] for a in top10]
        colors = ["#ef4444" if a["is_alert"] else "#334155" for a in top10]

        fig = go.Figure(go.Bar(
            x=scores,
            y=titles,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono", size=10, color="#94a3b8"),
            xaxis=dict(gridcolor="#1e293b", range=[0, 45]),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=0, b=0),
            height=280,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Article cards
        for article in scored_articles[:5]:
            is_alert  = article.get("is_alert", False)
            card_cls  = "article-card alert" if is_alert else "article-card"
            badge_cls = "score-badge alert" if is_alert else "score-badge"
            alert_tag = " 🚨" if is_alert else ""

            st.markdown(
                f'<div class="{card_cls}">'
                f'<div class="article-title">{article["title"][:90]}{alert_tag}</div>'
                f'<div class="article-meta">'
                f'{article["source"]} · {article["published_at"][:10]} · '
                f'<span class="{badge_cls}">{article["risk_score"]}/45</span>'
                f' S:{article["severity"]} P:{article["proximity"]} X:{article["sector"]}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<div class="article-card">'
            '<div class="article-meta">No data yet — click ▶ Run Pipeline Now</div>'
            '</div>',
            unsafe_allow_html=True
        )


# ── RIGHT: Inventory + RFQs ──────────────────
with right:

    # Inventory Status
    st.markdown('<div class="section-header">// Inventory Status</div>', unsafe_allow_html=True)

    inventory = st.session_state.inventory
    if inventory:
        inv_df = pd.DataFrame(inventory)
        inv_df["status"] = inv_df.apply(
            lambda r: "⚠️ LOW" if r["current_stock_days"] < r["minimum_safe_days"] else "✅ OK",
            axis=1
        )
        inv_df["% of safe"] = (inv_df["current_stock_days"] / inv_df["minimum_safe_days"] * 100).round(0).astype(int)

        # Color code the stock days
        at_risk_names = {m["material"] for m in inventory_result.get("at_risk_materials", [])}

        fig2 = go.Figure()
        for _, row in inv_df.iterrows():
            color = "#ef4444" if row["material"] in at_risk_names else \
                    "#f97316" if row["current_stock_days"] < row["minimum_safe_days"] else "#22c55e"
            fig2.add_trace(go.Bar(
                name=row["material"],
                x=[row["material"].capitalize()],
                y=[row["current_stock_days"]],
                marker_color=color,
                marker_line_width=0,
                showlegend=False,
            ))

        # Add safe threshold line
        fig2.add_hline(
            y=30, line_dash="dot",
            line_color="#334155",
            annotation_text="30d safe",
            annotation_font_color="#334155",
            annotation_font_size=10,
        )

        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono", size=10, color="#94a3b8"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor="#1e293b", title="Days of Stock"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=220,
            barmode="group",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # At risk materials table
        at_risk_mats = inventory_result.get("at_risk_materials", [])
        if at_risk_mats:
            for mat in at_risk_mats:
                urgency = mat["urgency"]
                color   = {"CRITICAL": "alert-critical", "HIGH": "alert-high",
                           "MEDIUM": "alert-medium", "LOW": "alert-ok"}.get(urgency, "alert-ok")
                st.markdown(
                    f'<div class="article-card {"alert" if urgency in ("CRITICAL","HIGH") else ""}">'
                    f'<div class="article-title">'
                    f'{mat["material"].capitalize()} '
                    f'<span class="{color}">● {urgency}</span>'
                    f'</div>'
                    f'<div class="article-meta">'
                    f'{mat["current_stock_days"]}d stock · '
                    f'{mat["buffer_after_days"]}d after disruption · '
                    f'{mat["supplier_state"]}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown(
            '<div class="article-card">'
            '<div class="article-meta">No inventory data — run pipeline first</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # RFQ Preview
    st.markdown(" ")
    st.markdown('<div class="section-header">// AI-Drafted RFQs (Dry Run)</div>', unsafe_allow_html=True)

    rfqs = st.session_state.rfqs
    if rfqs:
        for rfq in rfqs[:3]:   # Show first 3
            st.markdown(
                f'<div class="vendor-name">→ {rfq["name"]} · {rfq["location"]}</div>'
                f'<div class="rfq-card">{rfq["message"]}</div>',
                unsafe_allow_html=True
            )
        if len(rfqs) > 3:
            st.markdown(
                f'<div class="article-meta">+ {len(rfqs) - 3} more RFQs generated</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            '<div class="article-card">'
            '<div class="article-meta">No RFQs yet — run pipeline first</div>'
            '</div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────
# RISK HISTORY CHART
# ─────────────────────────────────────────────

st.markdown(" ")
st.markdown('<div class="section-header">// Risk Score History (30-day rolling window)</div>', unsafe_allow_html=True)

history = load_history()
if history and len(history) > 1:
    hist_df = pd.DataFrame(history)
    hist_df["date"] = pd.to_datetime(hist_df["date"])
    hist_df = hist_df.sort_values("date")

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=hist_df["date"],
        y=hist_df["max_score"],
        mode="lines+markers",
        line=dict(color="#3b82f6", width=2),
        marker=dict(size=6, color="#3b82f6"),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.08)",
        name="Max Risk Score",
    ))
    fig3.add_hline(
        y=25, line_dash="dot",
        line_color="#ef4444",
        annotation_text="alert threshold",
        annotation_font_color="#ef4444",
        annotation_font_size=10,
    )
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Mono", size=10, color="#94a3b8"),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b", range=[0, 46], title="Risk Score"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=180,
        showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.markdown(
        '<div class="article-card">'
        '<div class="article-meta">History builds after each pipeline run. '
        'Run the pipeline daily to see trends emerge.</div>'
        '</div>',
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

st.divider()
st.markdown(
    '<div class="timestamp" style="text-align:center">'
    'Supply Chain Disruption Alert Agent · Built for IIMA AI Summer Residency 2025 · '
    'Powered by NewsAPI · NVIDIA NIM (Llama 3.3 70B) · Twilio WhatsApp'
    '</div>',
    unsafe_allow_html=True
)