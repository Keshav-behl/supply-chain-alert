# 🏭 Supply Chain Disruption Alert Agent
### Autonomous procurement protection for Indian SME manufacturers

---

## What It Does

Indian SME manufacturers lose significant working capital when supply chain disruptions hit — floods, port delays, fuel shortages, strikes — and they find out **24–48 hours too late** to act.

This agent:
1. **Detects** disruptions by scanning news, live weather, and port signals every 6 hours
2. **Scores** each signal by severity, proximity, and sector relevance
3. **Detects anomalies** statistically using Z-score against 30-day rolling history
4. **Checks inventory** — do you have enough buffer stock to ride out the disruption?
5. **Contacts** backup vendors on WhatsApp with AI-drafted RFQs (Llama 3.3 70B)
6. **Parses** vendor replies — even freeform Hindi-English messages
7. **Presents** the owner a ranked vendor comparison for one-tap approval
8. **Persists** everything to Supabase for historical analysis

> No ERP integration. No app to install. Just WhatsApp.

---

## System Architecture

```
Every 6 hours (scheduler.py)
           │
           ▼
┌──────────────────────┐
│    Data Ingestion    │  NewsAPI + Open-Meteo + Port Monitor
│  news + weather +    │  15 risk keywords, 6 Gujarat cities,
│  port signals        │  4 major Indian ports
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│    Risk Scorer       │  Score = Severity × Proximity × Sector
│                      │  Max score: 45 | Alert threshold: 20
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│  Anomaly Detector    │  Z-score on 30-day rolling history
│                      │  Falls back to threshold for first 5 days
└─────────┬────────────┘
          │ (if anomaly detected)
          ▼
┌──────────────────────┐
│  Inventory Manager   │  Loads stock levels from CSV
│  Threshold Checker   │  Cross-references disruption vs buffer stock
└─────────┬────────────┘
          │ (if action required)
          ▼
┌──────────────────────┐
│   Vendor Registry    │  Backup vendors per material
│   RFQ Generator      │  Llama 3.3 70B drafts WhatsApp messages
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│  WhatsApp Agent      │  Sends RFQs via Twilio (dry run by default)
│  Response Parser     │  LLM extracts price/qty/lead from replies
│  Owner Approval      │  Ranked comparison → one-tap confirmation
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│  Supabase Database   │  Persists all runs, articles, RFQs
│  Streamlit Dashboard │  Live risk charts + inventory status
└──────────────────────┘
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.13 | Data ecosystem, fastest prototyping |
| News Data | NewsAPI | India-filtered, 15 risk keywords |
| Weather | Open-Meteo | Free, no API key, lat/lon based |
| Port Data | NewsAPI + port keywords | JNPT, Mundra, Kandla, Chennai |
| Anomaly Detection | Scikit-learn + NumPy | Z-score on rolling history |
| LLM — RFQ + Parser | NVIDIA NIM (Llama 3.3 70B) | Free, OpenAI-compatible API |
| Database | Supabase (PostgreSQL) | Free tier, real-time |
| WhatsApp | Twilio WhatsApp API | Industry standard |
| Scheduler | APScheduler | Runs every 6 hours automatically |
| Dashboard | Streamlit + Plotly | Ships fast, looks credible |

---

## Project Structure

```
supply-chain-alert/
│
├── data_ingestion/
│   ├── news_fetcher.py       ← NewsAPI, 15 risk keywords, source blocklist
│   ├── weather_fetcher.py    ← Open-Meteo, 6 Gujarat manufacturing hubs
│   └── port_fetcher.py       ← JNPT, Mundra, Kandla, Chennai port signals
│
├── processing/
│   ├── risk_scorer.py        ← Severity × Proximity × Sector (max 45)
│   └── anomaly_detector.py   ← Z-score on 30-day rolling history
│
├── inventory/
│   ├── inventory_manager.py  ← Loads stock levels from CSV
│   └── threshold_checker.py  ← Cross-references disruption vs buffer
│
├── vendor_network/
│   ├── vendor_registry.py    ← Backup vendor database per material
│   └── rfq_generator.py      ← Llama 3.3 70B drafts WhatsApp RFQs
│
├── whatsapp_agent/
│   ├── outbound_rfq.py       ← Sends via Twilio (dry run by default)
│   └── response_parser.py    ← LLM extracts structured data from replies
│
├── approval_flow/
│   └── owner_approval.py     ← Ranked comparison → owner WhatsApp
│
├── database/
│   ├── models.py             ← PostgreSQL schema + connection
│   └── crud.py               ← Save/fetch pipeline runs, articles, RFQs
│
├── dashboard/
│   └── app.py                ← Streamlit dashboard
│
├── inventory/
│   └── sample_inventory.csv  ← 8 raw materials with stock levels
│
├── vendor_network/
│   └── sample_vendors.json   ← Backup vendors for 5 materials
│
├── main.py                   ← Full pipeline — single run
├── scheduler.py              ← Runs pipeline every 6 hours automatically
├── requirements.txt
└── .env.example
```

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/Keshav-behl/supply-chain-alert.git
cd supply-chain-alert

# 2. Virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Set up database (run SQL in Supabase SQL Editor)
python database/models.py

# 6. Single pipeline run
python main.py

# 7. Automated — runs every 6 hours
python scheduler.py
```

---

## API Keys Required

| Service | Free Tier | Link |
|---|---|---|
| NewsAPI | 100 req/day | [newsapi.org](https://newsapi.org/register) |
| Open-Meteo | Unlimited | No key needed |
| NVIDIA NIM | Free developer tier | [build.nvidia.com](https://build.nvidia.com) |
| Supabase | 500MB database | [supabase.com](https://supabase.com) |
| Twilio WhatsApp | Sandbox free | [twilio.com](https://twilio.com/whatsapp) |

---

## Live Test Results

Running against live data (March 2026):

```
[1] Score: 30/45 🚨 ALERT
    Title    : LPG shortage fears — fuel supply disruption signals
    Severity : 5 | Proximity: 2 | Sector: 3
    Source   : Times of India

[2] Score: 27/45 🚨 ALERT
    Title    : Iran war drives fuel shortage fears across India
    Severity : 3 | Proximity: 3 | Sector: 3
    Source   : Indian Express

Materials flagged:
  Diesel   → HIGH  (15d stock, 1d buffer after disruption)
  Cement   → HIGH  (28d stock, drops below 30d safe level)
  Cotton   → MEDIUM (35d stock, 21d buffer)

RFQs generated: 9 (3 vendors × 3 materials)
Vendor replies parsed: Hindi + English freeform → structured data
Owner approval message: Ranked comparison sent to WhatsApp
```

---

## Roadmap

- [x] Multi-source data ingestion (news + weather + ports)
- [x] Statistical anomaly detection (Z-score)
- [x] Inventory cross-referencing
- [x] AI-drafted vendor RFQs (Llama 3.3 70B)
- [x] Response parser (Hindi/English freeform → structured)
- [x] Owner approval flow
- [x] Supabase persistence
- [x] Streamlit dashboard
- [x] Automated scheduler (6-hour runs)
- [ ] Twilio WhatsApp live (dry run → live flip)
- [ ] Google Sheets inventory sync
- [ ] Multi-region expansion (beyond Gujarat)
- [ ] Vendor response tracking loop

---

## Built For

**IIMA AI Summer Residency 2026** — solving real Indian manufacturing problems with AI-native tooling.

*Built by Keshav Behl*