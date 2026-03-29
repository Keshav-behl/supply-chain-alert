# 🏭 Supply Chain Disruption Alert Agent
### Autonomous procurement protection for Indian SME manufacturers

---

## What It Does

Indian SME manufacturers lose significant working capital when supply chain disruptions hit — floods, port delays, fuel shortages, strikes — and they find out **24–48 hours too late** to act.

This system:
1. **Detects** disruptions by scanning news, weather, and port data every 6 hours
2. **Scores** each disruption by severity, proximity, and sector relevance
3. **Checks** your inventory — do you have enough buffer stock?
4. **Contacts** backup vendors on WhatsApp with an auto-drafted RFQ
5. **Summarises** vendor responses and sends you a one-tap approval request

> No ERP integration. No app to install. Just WhatsApp.

---

## System Architecture

```
Every 6 hours
      │
      ▼
┌─────────────────────┐
│   Data Ingestion    │  NewsAPI + OpenWeatherMap + Port RSS feeds
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Risk Scorer       │  Score = Severity × Proximity × Sector Relevance
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Anomaly Detector   │  Isolation Forest — is this score unusual?
└────────┬────────────┘
         │ (if anomaly detected)
         ▼
┌─────────────────────┐
│  Inventory Checker  │  Do you have >30 days buffer for affected material?
└────────┬────────────┘
         │ (if buffer low)
         ▼
┌─────────────────────┐
│   Vendor Agent      │  Finds 3 backup vendors, LLM drafts RFQ
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  WhatsApp Delivery  │  RFQ → vendors │ Ranked summary → owner
└─────────────────────┘
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.11 |
| News Data | NewsAPI |
| Weather | OpenWeatherMap |
| Anomaly Detection | Scikit-learn (Isolation Forest) |
| LLM Summarization | Claude API (claude-haiku) |
| Database | Supabase |
| WhatsApp | Twilio WhatsApp API |
| Dashboard | Streamlit |
| Hosting | Railway.app |

---

## Project Structure

```
supply-chain-alert/
├── data_ingestion/
│   ├── news_fetcher.py       ← START HERE
│   ├── weather_fetcher.py
│   └── port_fetcher.py
├── processing/
│   ├── risk_scorer.py
│   └── anomaly_detector.py
├── inventory/
│   ├── inventory_manager.py
│   └── threshold_checker.py
├── vendor_network/
│   ├── vendor_registry.py
│   └── rfq_generator.py
├── whatsapp_agent/
│   ├── outbound_rfq.py
│   └── response_parser.py
├── approval_flow/
│   └── owner_approval.py
├── database/
│   └── models.py
├── dashboard/
│   └── app.py
├── main.py
├── config.py
├── requirements.txt
└── .env.example
```

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/supply-chain-alert.git
cd supply-chain-alert

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Test the news fetcher
python -m data_ingestion.news_fetcher
```

---

## API Keys Needed (All Free Tier)

| Service | Free Tier | Link |
|---|---|---|
| NewsAPI | 100 req/day | [newsapi.org](https://newsapi.org/register) |
| OpenWeatherMap | 1000 req/day | [openweathermap.org](https://openweathermap.org/api) |
| Supabase | 500MB DB | [supabase.com](https://supabase.com) |
| Twilio WhatsApp | Sandbox free | [twilio.com](https://twilio.com/whatsapp/sandbox) |
| Anthropic Claude | $5 free credit | [console.anthropic.com](https://console.anthropic.com) |

---

## Built For

IIMA AI Summer Residency 2026 — solving real Indian manufacturing problems with AI-native tooling.

---

*Built by Keshav Behl*
