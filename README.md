# Wealthsimple AI Tax Analyzer

AI-native tax document analysis and financial optimization engine. Ingests Canadian tax documents (T4, T5, T2202), extracts data via OCR + GPT-4o Vision, redacts PII, analyzes with GPT-4o against 20+ tax strategies, enriches insights with a LightRAG knowledge graph of CRA tax law, and surfaces prioritized recommendations — gated by human advisor review.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, async SQLite (aiosqlite) |
| **AI/ML** | OpenAI GPT-4o (analysis + vision OCR), GPT-4o-mini (knowledge graph) |
| **RAG** | LightRAG (graph-based retrieval with NetworkX + NanoVectorDB) |
| **OCR** | PyMuPDF spatial extraction + GPT-4o Vision fallback |
| **Frontend** | React 19, Vite 7, TypeScript, Recharts |
| **Testing** | pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend) |
| **Security** | PII redaction, rate limiting (SlowAPI), API key auth |
| **DevOps** | Docker, docker-compose, nginx |

## Architecture

```
PDF Upload → OCR Extraction → PII Redaction → Profile Creation
                                                     ↓
                                    ┌────────────────┼────────────────┐
                                    ↓                ↓                ↓
                              Tax Engine        GPT-4o LLM      LightRAG Query
                              (deterministic)   (insights)      (CRA knowledge)
                                    └────────────────┼────────────────┘
                                                     ↓
                                              Benefit Engine
                                           (prioritize + enrich)
                                                     ↓
                                              Advisor Review
                                           (approve/reject/escalate)
                                                     ↓
                                             Approved Insights
                                          (dashboard + PDF report)
```

See [docs/architecture.md](docs/architecture.md) for detailed Mermaid diagrams.

## Quick Start

### Docker (Recommended)

```bash
# Clone and configure
cp .env.example .env
# Set OPENAI_API_KEY in .env

# Start both services
docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

#### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173` (proxies API to backend)

#### Ingest Knowledge Base

```bash
# After backend is running:
curl -X POST http://localhost:8000/api/knowledge/ingest
```

## Usage Flow

1. **Upload** — Upload T4/T5 PDF or image at `/`. OCR extracts and redacts PII automatically.
2. **Analysis** — Click "Run Full Analysis" to trigger the pipeline. Watch real-time SSE progress:
   - Extraction → Tax Engine → GPT-4o Analysis → Knowledge Graph Query → Insight Generation
3. **Dashboard** — View charts: savings by category (bar), savings breakdown (pie), confidence meter.
4. **Insights** — See prioritized insights with expandable details, calculations, and CRA guidance.
5. **PDF Report** — Download a branded PDF report of all approved insights.
6. **Trends** — View multi-year income, tax, and savings trends across tax years.
7. **Advisor** — Review queue with SLA tracking. Approve, reject, modify, or escalate cases.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload PDF/image, returns extracted fields |
| `POST` | `/api/profiles` | Create financial profile from extracted data |
| `POST` | `/api/analyze/{id}` | Trigger full analysis pipeline |
| `GET` | `/api/analyze/{id}/stream` | SSE stream of pipeline progress |
| `GET` | `/api/analysis/{id}/status` | Analysis status |
| `GET` | `/api/analysis/{id}/results` | Approved insights |
| `GET` | `/api/analysis/{id}/dashboard` | Chart-ready dashboard data |
| `GET` | `/api/trends` | Multi-year trend data |
| `GET` | `/api/reports/{id}/pdf` | Download PDF report |
| `GET` | `/api/advisor/queue` | Pending review cases |
| `GET` | `/api/advisor/case/{id}` | Case detail with insights |
| `POST` | `/api/advisor/case/{id}/approve` | Approve case |
| `POST` | `/api/advisor/case/{id}/reject` | Reject case |
| `POST` | `/api/advisor/case/{id}/escalate` | Escalate case |
| `POST` | `/api/knowledge/ingest` | Ingest CRA knowledge base |
| `POST` | `/api/knowledge/query` | Query tax knowledge graph |
| `GET` | `/health` | Health check |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key for GPT-4o and embeddings |
| `DATABASE_URL` | No | `sqlite:///./t4_analyzer.db` | Database connection string |
| `MAX_FILE_SIZE_MB` | No | `10` | Max upload file size |
| `API_KEYS` | No | — | Comma-separated API keys (auth disabled if unset) |
| `ENVIRONMENT` | No | `production` | `development` enables SQL echo logging |

## Testing

```bash
# Backend tests (75 tests)
cd backend && python -m pytest tests/ -v

# Frontend tests (22 tests)
cd frontend && npx vitest run
```

## Multi-Document Support

| Document | Status | Extracted Fields |
|----------|--------|-----------------|
| **T4** | Full support | Boxes 14, 16, 18, 22, 24, 26, 44, 46, 50, 52, province, year |
| **T5** | Supported | Boxes 13, 18, 24, 25, 26 (interest, dividends, capital gains) |
| **T2202** | Vision fallback | Tuition amounts, institution |
| **NOA** | Vision fallback | Assessment details |

## Knowledge Base

9 CRA-sourced knowledge documents powering the LightRAG knowledge graph:

- RRSP rules (T4040) — contribution limits, HBP, LLP, spousal RRSP
- TFSA rules (RC4466) — annual limits, withdrawal/recontribution
- CPP/EI rates (T4127) — rates, YMPE, max contributions 2020-2025
- Federal tax brackets — brackets, BPA, credits 2020-2025
- Ontario tax — provincial brackets, surtax, health premium
- Tax planning strategies — RRSP/TFSA optimization, loss harvesting
- Employment income (T4 Guide) — box-by-box reference
- Investment income (T5) — dividend gross-up, interest taxation
- Education credits (T2202) — tuition credits, transfer rules
