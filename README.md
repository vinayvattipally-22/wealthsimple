# TaxFolio AI

AI-native Canadian tax analysis and year-round financial planning platform. Upload your T4, T5, or T2202 — the system extracts data via OCR + GPT-4o Vision, redacts PII before any external call, runs a full tax optimization analysis, queries a knowledge graph of CRA tax law, and surfaces prioritized recommendations — every insight approved by a human advisor before you see it.

---

## What It Does

| Without TaxFolio | With TaxFolio |
|-----------------|--------------|
| ~15 min manual data entry | 10 seconds — automatic OCR extraction |
| ~2–4 hours advisor consultation | 15 seconds — GPT-4o evaluates 20+ strategies |
| ~30 min CRA research | 2 seconds — LightRAG queries 20 CRA documents |
| ~3–5 hours stock research | 30 seconds — 6-stage AI pipeline |

---

## Features

### Document Intelligence
- **Multi-format OCR** — PyMuPDF spatial extraction + GPT-4o Vision fallback for T4, T5, T2202, NOA
- **PII Redaction** — Deterministic masking of SIN, credit cards, addresses, postal codes, DOB, and passport numbers *before* any external API call or database write
- **Multi-year support** — Track and compare documents across tax years 2020–2025

### Tax Analysis Pipeline (8+ LLM calls per analysis)
- **Deterministic Tax Engine** — Federal + provincial calculations for all 13 provinces/territories with CPP/EI, benefit phase-outs, and surtax
- **LLM Strategy Evaluation** — GPT-4o evaluates 20+ optimization strategies against the user's actual numbers
- **LightRAG Knowledge Graph** — 20 CRA documents (476 nodes, 398 edges) queried per analysis for applicable rules and credits
- **Benefit Engine** — 40+ insight types, 3-tier urgency (ACT_NOW / THIS_YEAR / LONG_TERM), dollar value estimates with visible calculations
- **Anomaly Detection** — Flags outlier tax rates, income discrepancies, and edge cases for advisor escalation
- **Real-time Progress** — SSE streaming shows each pipeline stage as it completes

### Advisor Quality Control
- Human advisor reviews every AI-generated insight before delivery
- Approve / reject / modify / escalate workflow
- 24-hour SLA tracking with confidence-based prioritization
- Full audit trail (who reviewed what, when, and what decision was made)

### Scenario Simulator
Model the tax impact of financial decisions before making them:
- RRSP contribution (up to annual RRSP max)
- TFSA contribution
- FHSA contribution (if eligible)
- Income change (higher or lower income)
- Province change (relocation planning)

Each scenario returns: federal tax, provincial tax, marginal rate, effective rate, take-home pay, GST/HST credit, and CWB eligibility.

### Stock Research (6-Stage AI Pipeline)
1. **Market Data** — Price, 52-week range, PE ratio, dividend yield via yfinance
2. **Technical Analysis** — SMA (20/50/200), RSI, MACD, Bollinger Bands
3. **Sentiment Analysis** — GPT-4o batch-scores recent news articles (bullish/neutral/bearish)
4. **Geo-Policy Analysis** — Regulatory and geopolitical risk assessment
5. **Risk Analysis** — Volatility, Sharpe ratio, max drawdown
6. **Outlook** — Aggregated buy/hold/sell signal with confidence score

### Tax Copilot Chat
Context-aware AI assistant with access to the user's financial profile, current insights, and action items. Responds via SSE streaming. Scoped to tax and finance topics.

### Multi-Year Trends & Financial Health
- Year-over-year income, tax liability, and savings visualization (Recharts)
- Financial health score with personalized analysis
- Projected RRSP/TFSA growth curves

### PDF Reports
Downloadable branded PDF reports (ReportLab) covering all approved insights, calculations, and CRA guidance.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 7, TypeScript, React Router 7, Recharts, Lucide Icons |
| **Backend** | Python 3.11, FastAPI, async SQLAlchemy 2.0, aiosqlite |
| **AI/LLM** | OpenAI GPT-4o (analysis + Vision OCR), GPT-4o-mini (RAG entity extraction) |
| **RAG** | LightRAG 1.0.0 (graph-based retrieval, NetworkX + NanoVectorDB) |
| **OCR** | PyMuPDF spatial block analysis + GPT-4o Vision fallback |
| **Auth** | JWT tokens (python-jose), bcrypt password hashing |
| **Stock Data** | yfinance, Alpha Vantage API |
| **Reports** | ReportLab 4.0+ PDF generation |
| **Database** | SQLite (async, auto-initializes on startup) |
| **Testing** | pytest + pytest-asyncio (75 backend tests), Vitest + Testing Library (22 frontend tests) |
| **DevOps** | Docker, docker-compose, nginx |

---

## Architecture

```
PDF / Image Upload
        │
┌───────▼────────────────────────────────┐
│  Document Intelligence Pipeline        │
│  PyMuPDF → Regex → GPT-4o Vision      │
│  (3-layer extraction with fallbacks)   │
└───────┬────────────────────────────────┘
        │
┌───────▼────────────────────────────────┐
│  PII Redaction                         │
│  SIN, CC, addresses, postal, DOB       │
│  (deterministic, before any API call)  │
└───────┬────────────────────────────────┘
        │
        ├──────────────────────────────────┐
        ▼                ▼                 ▼
  Tax Engine        GPT-4o LLM        LightRAG Query
  (deterministic)   (20+ strategies)  (CRA knowledge graph)
        │                │                 │
        └────────────────┼─────────────────┘
                         ▼
                  Benefit Engine
             (40+ insight types, priority, value)
                         │
                         ▼
                  Anomaly Detector
                (outliers, escalation flags)
                         │
                         ▼
                  Advisor Review Queue
              (approve / reject / escalate)
                         │
                         ▼
            Dashboard + Insights + PDF Report
```

See [docs/architecture.md](docs/architecture.md) for detailed Mermaid diagrams.

---

## Quick Start

### Docker (Recommended)

```bash
# Clone and configure
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Start both services
docker-compose up --build

# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
```

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
# Backend: http://127.0.0.1:8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Frontend: http://localhost:5173 (proxies /api/* to backend)
```

> The knowledge base (20 CRA documents) is auto-ingested on first backend startup. No manual step required.

---

## Demo Flow

1. **Register** — Create an account and select your province
2. **Upload** — Drag-and-drop a T4 PDF; watch OCR extract fields and PII get redacted
3. **Analyze** — Click "Run Full Analysis"; watch the SSE pipeline progress in real time
4. **Dashboard** — Review income breakdown, tax owed, savings opportunities, and confidence score
5. **Insights** — Expand each insight to see calculations, CRA basis, and estimated dollar impact
6. **Simulate** — Open the Simulator and model an RRSP contribution or province change
7. **Action Items** — View generated tasks with CRA deadlines
8. **Stock Research** — Search a ticker and run the 6-stage AI research pipeline
9. **Advisor Dashboard** — Switch to advisor role and approve/reject the pending review case
10. **PDF Report** — Download the branded analysis report

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | GPT-4o and embedding access |
| `ALPHA_VANTAGE_API_KEY` | No | — | Stock news sentiment (free tier: 25 req/day) |
| `LLM_MODEL` | No | `gpt-4o` | Override the default LLM model |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./t4_analyzer.db` | Database connection string |
| `MAX_FILE_SIZE_MB` | No | `10` | Max upload file size |
| `ENVIRONMENT` | No | `production` | `development` enables SQL echo logging |
| `NEWS_REFRESH_INTERVAL_HOURS` | No | `4` | Stock news background refresh interval |
| `MAX_TRACKED_STOCKS` | No | `2` | Max tickers for scheduled news refresh |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create user account |
| `POST` | `/api/auth/login` | Get JWT token |
| `POST` | `/api/upload` | Upload PDF/image, returns extracted fields |
| `POST` | `/api/profiles` | Create financial profile from extracted data |
| `POST` | `/api/analyze/{id}` | Trigger full analysis pipeline |
| `GET` | `/api/analyze/{id}/stream` | SSE stream of pipeline progress |
| `GET` | `/api/analysis/{id}/status` | Analysis status |
| `GET` | `/api/analysis/{id}/results` | Approved insights |
| `GET` | `/api/analysis/{id}/dashboard` | Chart-ready dashboard data |
| `POST` | `/api/simulator/scenario` | Run a what-if tax scenario |
| `GET` | `/api/trends` | Multi-year trend data |
| `GET` | `/api/action_items` | Trackable tasks with CRA deadlines |
| `GET` | `/api/reports/{id}/pdf` | Download PDF report |
| `GET` | `/api/advisor/queue` | Pending review cases (advisor only) |
| `POST` | `/api/advisor/case/{id}/approve` | Approve case |
| `POST` | `/api/advisor/case/{id}/reject` | Reject case |
| `POST` | `/api/advisor/case/{id}/escalate` | Escalate case |
| `GET` | `/api/stocks/search` | Search tickers |
| `GET` | `/api/stocks/research/{ticker}/stream` | SSE stream of 6-stage stock analysis |
| `GET` | `/api/stocks/news/{ticker}` | Fetch and score stock news |
| `POST` | `/api/chat` | Streaming tax copilot response |
| `POST` | `/api/knowledge/ingest` | Re-ingest CRA knowledge base |
| `POST` | `/api/knowledge/query` | Query tax knowledge graph directly |
| `GET` | `/health` | Health check |

Full interactive API docs: `http://localhost:8000/docs`

---

## Document Support

| Document | Extraction | Extracted Fields |
|----------|-----------|-----------------|
| **T4** | Full (PyMuPDF + Vision) | Boxes 14, 16, 18, 22, 24, 26, 44, 46, 50, 52, province, year |
| **T5** | Full | Boxes 13, 18, 24, 25, 26 (interest, dividends, capital gains) |
| **T2202** | Vision fallback | Tuition amounts, institution, part-time/full-time months |
| **NOA** | Vision fallback | Assessment year, total income, tax payable, balance owing |

---

## Knowledge Base (20 CRA Documents)

The LightRAG graph is auto-ingested on startup and contains 476 nodes and 398 edges:

- **Federal**: Tax brackets (2020–2025), BPA, benefits, credits
- **Accounts**: RRSP rules, TFSA rules, FHSA rules, CPP/EI rates, FHSA eligibility
- **Income**: T4 employment income guide, T5 investment income, T2202 education credits
- **Planning**: Capital gains rules, tax optimization strategies, policy changes 2021–2025
- **Deadlines**: CRA key dates and filing deadlines
- **Provincial**: Ontario, BC, Alberta, Quebec, and other province-specific brackets and credits

---

## Testing

```bash
# Backend — 75 tests
cd backend
python -m pytest tests/ -v

# Frontend — 22 tests
cd frontend
npx vitest run
```

Test coverage includes: tax engine accuracy, OCR extraction, PII redaction, benefit engine insight generation, and API integration end-to-end flows.

---

## Project Structure

```
taxfolio/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── routers/                 # 18 API route modules (~100+ endpoints)
│   ├── services/                # 20+ business logic services (~5,100 lines)
│   ├── models/                  # SQLAlchemy ORM models
│   ├── rules/                   # Deterministic tax tables (brackets, CPP/EI, limits)
│   ├── prompts/                 # Structured LLM prompt templates
│   ├── knowledge/               # 20 CRA markdown documents for LightRAG
│   ├── middleware/              # JWT auth, rate limiting, API key auth
│   └── tests/                   # pytest test suite (75 tests)
├── frontend/
│   ├── src/
│   │   ├── pages/               # 13 pages (Dashboard, Insights, Simulator, Stocks, etc.)
│   │   └── components/          # Reusable UI components
│   └── vite.config.js           # Vite dev server with API proxy
├── docs/                        # Architecture diagrams, pitch documents
├── docker-compose.yml
└── .env.example
```

---

## Security

- **PII Redaction** — 10+ pattern types (SIN, CC, phone, email, postal, address, DOB, passport, driver's license) stripped before any storage or API call
- **JWT Authentication** — 30-minute token expiration, bcrypt password hashing
- **Rate Limiting** — 10 analyses/hour, 100 reads/hour per user (SlowAPI)
- **Role-Based Access** — Advisor-only routes protected by role middleware
- **Prompt Injection Protection** — Analysis prompts include explicit scope-limiting rules
- **Audit Logging** — All advisor decisions logged with timestamps and reviewer identity
