# Wealthsimple AI Tax Analyzer — Application Overview

## Purpose

The Wealthsimple AI Tax Analyzer is an AI-native platform that automates Canadian personal tax analysis and financial planning. Users upload tax documents (T4, T5, T2202), and the system automatically extracts data, calculates tax liability, identifies savings opportunities, and delivers actionable recommendations — all within seconds.

The platform also includes an AI-powered stock research module for market analysis.

---

## How It Works

### Tax Analysis Pipeline

1. **Upload** — User uploads a tax document (PDF or image)
2. **Extract** — OCR + GPT-4o Vision reads and extracts all fields automatically
3. **Redact** — PII (SIN, employer info) is masked before storage or LLM processing
4. **Calculate** — Deterministic tax engine computes federal + provincial liability using CRA brackets (2020–2025)
5. **Analyze** — GPT-4o evaluates 20+ tax optimization strategies against the user's actual numbers
6. **Enrich** — LightRAG knowledge base (476 nodes, 398 edges) retrieves relevant CRA rules and provincial credits
7. **Prioritize** — Benefit engine combines all results into prioritized insights with estimated dollar savings
8. **Review** — Human advisor approves/modifies insights before delivery (quality gate)
9. **Deliver** — Dashboard, insights, action items, and downloadable PDF report

### Stock Research Pipeline

1. **Market Data** — Fetches current price, financials, 52-week range
2. **Technical Analysis** — Computes SMA, RSI, MACD, Bollinger Bands
3. **Sentiment Analysis** — LLM scores recent news articles (bullish/neutral/bearish)
4. **Geo-Policy Analysis** — Assesses regulatory and geopolitical risks
5. **Risk Analysis** — Calculates volatility, Sharpe ratio, max drawdown
6. **Outlook** — Aggregates all analyses into short/mid/long-term price direction

---

## Reducing Human Intervention

| Task | Traditional Approach | With This App |
|------|---------------------|---------------|
| Reading tax documents | User manually enters T4 box values | OCR + GPT-4o Vision reads and extracts automatically |
| Tax calculations | Error-prone spreadsheets or paid software | Deterministic engine with CRA brackets, instant |
| Finding savings opportunities | Requires a tax advisor ($200–500/session) | 20+ strategies evaluated in ~15 seconds |
| Knowing provincial credits | Manual search through government websites | LightRAG retrieves all applicable credits instantly |
| Prioritizing what to act on | Advisor judgment, often missed | Automatic priority scoring (ACT_NOW / THIS_YEAR / LONG_TERM) |
| Year-over-year comparison | Re-enter data, manual comparison | Automatic multi-year trend analysis |
| Creating an action plan | Verbal advice, no tracking | Trackable action items with CRA deadlines |
| Scenario planning | Complex spreadsheets | Real-time what-if simulator (RRSP, TFSA, FHSA, income, province) |
| Quality assurance | Single review, easy to miss errors | Structured advisor review queue with 24-hour SLA and audit trail |
| Stock research | Hours of manual news reading and chart analysis | 6-stage AI pipeline delivers results in seconds |
| News sentiment | Read articles one by one | Batch LLM scoring of 20 articles at once |
| Report generation | Manual Word/PDF creation | Auto-generated branded PDF with all insights and calculations |

---

## AI Workload Reduction

### Where AI Is Used (8+ LLM Calls Per Analysis)

| AI Component | What It Does | Time Saved |
|-------------|-------------|-----------|
| **GPT-4o Vision OCR** | Reads scanned documents, extracts T4/T5 fields | ~15 min of manual data entry per document |
| **Extraction Verification** | Validates extracted fields for accuracy | ~5 min of cross-checking |
| **Financial Analysis** | Evaluates 20+ tax strategies against user data | ~2–4 hours of advisor consultation |
| **RAG Knowledge Retrieval** | Queries 20 CRA knowledge documents for applicable rules | ~30 min of research per question |
| **Benefit Engine** | Generates provincial-specific credit recommendations | ~1 hour of province-specific research |
| **Scenario Simulator** | Models RRSP/TFSA/income/province-change impact | ~1 hour of spreadsheet modeling |
| **Stock Sentiment Analysis** | Batch scores news articles for market sentiment | ~2 hours of manual news reading |
| **Stock Outlook Aggregation** | Combines technicals + sentiment + risk into a signal | ~3 hours of manual analysis |

### By the Numbers

- **Document processing**: From ~15 minutes (manual entry) to ~10 seconds (automated)
- **Tax optimization analysis**: From ~2–4 hours (advisor session) to ~15 seconds (AI pipeline)
- **Knowledge lookup**: From ~30 minutes (searching CRA website) to ~2 seconds (RAG query)
- **Stock research**: From ~3–5 hours (manual analysis) to ~30 seconds (6-stage pipeline)
- **Report generation**: From ~1 hour (manual PDF) to instant (auto-generated)

### Total Time Saved Per User

A typical user uploading one T4 and getting a full analysis:

- **Without the app**: ~4–6 hours (data entry + advisor consultation + research + action planning)
- **With the app**: ~2 minutes (upload + wait for analysis + review results)

That's a **~99% reduction in time** for the core tax analysis workflow.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Document Upload** | Drag-and-drop T4, T5, T2202, NOA documents |
| **AI Extraction** | Automatic field extraction with GPT-4o Vision |
| **Tax Dashboard** | Income, tax liability, savings, marginal rate at a glance |
| **Insights** | Prioritized savings opportunities with dollar estimates |
| **Action Items** | Trackable tasks with CRA deadlines |
| **What-If Simulator** | Model RRSP, TFSA, FHSA, income, and province-change scenarios |
| **AI Financial Advisor** | Health score, year-over-year comparison, personalized recommendations |
| **Trends** | Multi-year income, tax, and savings visualization |
| **Stock Research** | AI-powered market analysis with sentiment, technicals, and risk |
| **Advisor Review** | Human quality gate before insights reach users |
| **PDF Reports** | Downloadable branded reports with all findings |
| **Tax Copilot** | Context-aware AI chat assistant (available across all pages) |
| **Knowledge Base** | 20 CRA documents covering all provinces, 5 tax years (2021–2025) |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite, Recharts, Lucide Icons |
| **Backend** | FastAPI (Python), async SQLAlchemy, aiosqlite |
| **AI/LLM** | OpenAI GPT-4o (analysis), GPT-4o-mini (RAG extraction) |
| **Knowledge Base** | LightRAG (graph-based RAG, 476 nodes, 398 edges) |
| **OCR** | PyMuPDF spatial analysis + GPT-4o Vision fallback |
| **Database** | SQLite (async) |
| **Auth** | JWT tokens, bcrypt password hashing |
| **Stock Data** | yfinance, Alpha Vantage API |
| **Reports** | ReportLab PDF generation |

---

## Security

- **PII Redaction**: SIN, employer details masked before any LLM call or storage
- **Prompt Injection Protection**: All prompts include scope limiting and input sanitization rules
- **JWT Authentication**: 30-minute token expiration
- **Rate Limiting**: 10 analyses/hour, 100 reads/hour per user
- **Audit Logging**: All advisor review decisions logged with timestamps
- **Role-Based Access**: Advisor-only routes protected

---

## Architecture Summary

```
User uploads document
        |
        v
  [OCR + Vision] --> [Redact PII] --> [Store Document]
        |
        v
  [Tax Engine] --> [LLM Analysis] --> [RAG Query] --> [Benefit Engine]
        |
        v
  [Advisor Review Queue] --> Human approves/modifies
        |
        v
  [Dashboard + Insights + Action Items + PDF Report]
```

The system is designed so that AI handles the heavy lifting — reading documents, crunching numbers, finding opportunities, and generating reports — while humans provide the final quality check before insights reach the user.
