# 🚀 Keyword Intelligence & Campaign Automation Tool

> Built by [B Srikanth Reddy](https://linkedin.com/in/srikanthreddy) — Performance Marketing & Automation Lead at Clicksco Digital (Havas Group)

**Live Demo:** https://keyword-tool-automation.streamlit.app

---

## What this tool does

End-to-end Google Ads automation platform — from keyword discovery to campaign creation and real-time performance monitoring. Built for performance marketing professionals who want to eliminate 
manual work.

---

## Modules

### Module 1 — Keyword Research
- Google Autocomplete → 50+ keyword variations instantly
- Google Trends (PyTrends) → trend scores, rising keywords
- DataForSEO → real search volume, CPC, competition
- Opportunity Score (0-100) → prioritise which keywords to bid on
- Intent classification → BOFU / MOFU / TOFU
- Question keywords → for DSA and content campaigns
- Competitor research → who is ranking organically
- AI analysis (Groq Llama 3.3 70B) → clusters, ad groups, ad copy, negatives
- Export → CSV, Google Ads Editor format, Google Sheets

### Module 2 — Campaign Template Builder
- AI builds complete campaign structure from keyword clusters
- Ad groups by intent with keywords + match types
- Ad copy per ad group (headlines + descriptions)
- Negative keywords at campaign and ad group level
- Budget allocation by intent (BOFU/MOFU/TOFU)
- Export → Keywords CSV, Ads CSV, Negatives CSV, Google Sheets

### Module 3 — Anomaly Detection
- Connects to live campaign performance data
- Saves snapshots to BigQuery for historical comparison
- Detects anomalies: ROAS drop, CPA spike, CTR drop, impression share loss, quality score degradation
- Sends instant Telegram alerts
- 7-day rolling average comparison

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| AI Analysis | Groq API (Llama 3.3 70B) |
| Keyword Data | Google Autocomplete, PyTrends, DataForSEO |
| Storage | Google BigQuery |
| Sheets Export | Google Sheets API |
| Alerts | Telegram Bot API |
| Deployment | Streamlit Cloud |
| Infrastructure | Google Cloud Platform |

---

## Architecture
```
Keyword Input
      ↓
Google Autocomplete + PyTrends + DataForSEO
      ↓
Groq AI — clusters, intent, ad copy, negatives
      ↓
Campaign Builder — full structure with match types
      ↓
Export → Google Sheets / Google Ads Editor CSV
      ↓
Anomaly Detection → BigQuery → Telegram Alert
```

---

## Setup
```bash
git clone https://github.com/srikanthreddy979797-sys/keyword-tool
cd keyword-tool
pip install -r requirements.txt
cp .env.example .env  # add your API keys
streamlit run dashboard.py
```

### Required API Keys
```
GROQ_API_KEY         — groq.com (free)
DATAFORSEO_LOGIN     — dataforseo.com (freemium)
DATAFORSEO_PASSWORD  — dataforseo.com
TELEGRAM_BOT_TOKEN   — @BotFather on Telegram
TELEGRAM_CHAT_ID     — your Telegram chat ID
SHEETS_MASTER_ID     — your Google Sheet ID
```

---

## Built With

- 10+ years performance marketing experience
- Google Partner agency background
- Production-deployed on real campaigns

---

## Author

**B Srikanth Reddy**
Performance Marketing & Automation Lead
Clicksco Digital (Havas Group)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/srikanth-reddy-performance-marketing-lead/)
[![Live Demo](https://img.shields.io/badge/Live-Demo-green)](https://keyword-tool-automation.streamlit.app)
