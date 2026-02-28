Plan to implement                                                                             │
│                                                                                               │
│ Wealthsimple AI Tax Analyzer — Phase-Wise Implementation Plan                                 │
│                                                                                               │
│ Context                                                                                       │
│                                                                                               │
│ Build a full-stack AI-native tax document analysis and financial optimization engine for the  │
│ Wealthsimple AI Builder Submission. The system ingests Canadian T4/RRSP documents, extracts   │
│ data via OCR, redacts PII, analyzes with GPT-4o against 20+ tax optimization strategies, and  │
│ surfaces prioritized recommendations — all gated by human advisor review.                     │
│                                                                                               │
│ Stack: Python, FastAPI, OpenAI GPT-4o, React, SQLite (local file DB)                          │
│ Starting point: Greenfield — no existing code, only instructions.md, prompt_template.csv, and │
│  reference image                                                                              │
│                                                                                               │
│ Key Design Decisions                                                                          │
│                                                                                               │
│ - Database: SQLite local file (t4_analyzer.db) via SQLAlchemy — best fit for this prototype   │
│ (zero config, single-file, no external server needed, portable for demo)                      │
│ - LLM Prompts: All GPT-4o prompts will follow the structured template from                    │
│ prompt_template.csv with these fields:                                                        │
│   - aiRole — 2-5 word noun phrase identity tag (e.g., "Canadian Tax Document Parser")         │
│   - systemRole — Domain/Context/Audience/Tone/Compliance environment setup                    │
│   - objective — Success criteria (what a correct output looks like)                           │
│   - taskInstructions — STRICT RULES first, then numbered STEPS                                │
│   - taskInput — Field-level spec with required/optional and missing-data behavior             │
│   - taskOutputFormat — Exact JSON schema with field names, types, constraints                 │
│   - taskExample — NON-NORMATIVE example with realistic synthetic data                         │
│   - settingsJson — temperature, topP, max_tokens, response_format per task type               │
│                                                                                               │
│ ---                                                                                           │
│ Phase 1: Project Setup & Foundation (Est. ~30 min)                                            │
│                                                                                               │
│ Goal: Initialize the project structure, dependencies, and database layer.                     │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Create project directory structure matching the spec:                                      │
│ backend/                                                                                      │
│ ├── main.py                                                                                   │
│ ├── routers/  (upload, cra, analysis, advisor)                                                │
│ ├── services/ (ocr, redaction, reconciliation, llm, tax_engine, benefit_engine, audit)        │
│ ├── models/   (t4_schema, rrsp_schema, insight_schema, case_schema)                           │
│ ├── prompts/  (extraction_prompt, analysis_prompt, vision_prompt)                             │
│ ├── rules/    (federal_brackets, provincial_brackets, contribution_limits, cpp_ei_rates,      │
│ benefit_rates)                                                                                │
│ └── database/ (models.py)                                                                     │
│ frontend/                                                                                     │
│ ├── pages/    (Upload, Analysis, Insights, AdvisorDashboard)                                  │
│ ├── components/ (DocumentUploader, InsightCard, SavingsSummary, ReviewQueue, CaseDetail)      │
│ └── services/ (api.js, auth.js)                                                               │
│ 2. Create requirements.txt with: fastapi, uvicorn, pymupdf, openai, python-multipart,         │
│ sqlalchemy, aiosqlite, python-dotenv, pydantic                                                │
│ 3. Create .env template with OPENAI_API_KEY, DATABASE_URL=sqlite:///./t4_analyzer.db,         │
│ MAX_FILE_SIZE_MB=10, ENVIRONMENT=development                                                  │
│ 4. Create SQLite database layer (database/models.py):                                         │
│   - SQLAlchemy ORM with sqlite:///./t4_analyzer.db — local file, no server needed             │
│   - Tables: users, documents, financial_profiles, insights, review_cases, audit_logs          │
│   - Auto-create tables on app startup via Base.metadata.create_all()                          │
│   - Async session support via aiosqlite for FastAPI async endpoints                           │
│ 5. Create FastAPI app entry point (main.py) — CORS, router registration, DB init on startup   │
│ 6. Create backend/prompts/ directory — store all LLM prompt configurations as structured      │
│ Python dicts following the prompt_template.csv schema (aiRole, systemRole, objective,         │
│ taskInstructions, taskInput, taskOutputFormat, taskExample, settingsJson)                     │
│ 7. Initialize React frontend with Vite + basic routing setup                                  │
│                                                                                               │
│ Deliverable: Running FastAPI server + React dev server, empty database created on startup     │
│                                                                                               │
│ ---                                                                                           │
│ Phase 2: Data Models & Tax Rules Engine (Est. ~45 min)                                        │
│                                                                                               │
│ Goal: Build the deterministic tax rules engine and all Pydantic schemas.                      │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. T4 Schema (models/t4_schema.py) — Pydantic model for all T4 boxes (14–67), employer_name,  │
│ province_code, tax_year, confidence scores                                                    │
│ 2. RRSP Schema (models/rrsp_schema.py) — contribution amount, receipt date, issuer, plan type │
│ 3. Insight Schema (models/insight_schema.py) — id, priority, category, headline, detail,      │
│ estimated_value, calculation_shown, action_required, product_link, confidence,                │
│ requires_additional_info                                                                      │
│ 4. Case Schema (models/case_schema.py) — profile_id, insights list, review_status,            │
│ advisor_id, flags                                                                             │
│ 5. Federal tax brackets (rules/federal_brackets.py) — 2024/2025 5-bracket rates from Appendix │
│  A                                                                                            │
│ 6. Provincial tax brackets (rules/provincial_brackets.py) — All 13 provinces/territories      │
│ 7. Contribution limits (rules/contribution_limits.py) — RRSP, TFSA, FHSA annual/lifetime      │
│ limits by year                                                                                │
│ 8. CPP/EI rates (rules/cpp_ei_rates.py) — YMPE, YAMPE, max contributions, CPP2                │
│ 9. Benefit phase-out rates (rules/benefit_rates.py) — CCB, GST credit, OAS clawback, GIS      │
│ 10. Tax Engine service (services/tax_engine.py) — Deterministic calculations: marginal rate,  │
│ estimated liability, bracket analysis, over-withholding detection, CPP/EI overpayment         │
│                                                                                               │
│ Deliverable: All schemas validate correctly, tax engine computes correct marginal rates and   │
│ tax liability for sample data                                                                 │
│                                                                                               │
│ ---                                                                                           │
│ Phase 3: OCR + Extraction Pipeline (Est. ~45 min)                                             │
│                                                                                               │
│ Goal: Build the document ingestion pipeline — PDF text extraction, GPT-4o Vision fallback,    │
│ field parsing.                                                                                │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. OCR Service (services/ocr_service.py):                                                     │
│   - extract_t4(file_path) — main pipeline entry point                                         │
│   - _extract_digital(file_path) — PyMuPDF text extraction for digital PDFs                    │
│   - _extract_vision(file_path) — GPT-4o Vision for scanned/image documents                    │
│   - _parse_fields(raw_text) — Regex-based box number to value mapping                         │
│   - _validate_fields(fields) — Range validation (CPP max, EI max, tax rate anomaly)           │
│   - Confidence scoring per field                                                              │
│ 2. Upload Router (routers/upload.py):                                                         │
│   - POST /api/upload — accept PDF/image, size validation (10MB max), trigger extraction       │
│   - File type detection (digital PDF vs scanned PDF vs image)                                 │
│   - Return extracted fields + confidence scores                                               │
│ 3. Create sample/dummy T4 PDFs for testing (2-3 synthetic documents)                          │
│                                                                                               │
│ Deliverable: Upload a T4 PDF via API, get back structured JSON with all box values and        │
│ confidence scores                                                                             │
│                                                                                               │
│ ---                                                                                           │
│ Phase 4: PII Redaction Service (Est. ~30 min)                                                 │
│                                                                                               │
│ Goal: Build deterministic PII detection and masking — the privacy firewall before any         │
│ external API call.                                                                            │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Redaction Service (services/redaction_service.py):                                         │
│   - redact_pii(text_or_dict) — main entry point                                               │
│   - SIN pattern: \d{3}[\s-]\d{3}[\s-]\d{3} → [SIN-REDACTED]                                   │
│   - Postal code pattern: [A-Z]\d[A-Z]\s?\d[A-Z]\d → [POSTAL-REDACTED]                         │
│   - DOB pattern: \d{4}[-/]\d{2}[-/]\d{2} → [DOB-REDACTED]                                     │
│   - Name detection and removal (employer name retained as it's a business entity)             │
│   - Address line removal                                                                      │
│   - Return only financial figures and box numbers                                             │
│ 2. Integrate into OCR pipeline — redaction runs BEFORE any data is stored or sent externally  │
│ 3. Unit tests — verify SIN, postal code, DOB, name, address all redacted; financial figures   │
│ preserved                                                                                     │
│                                                                                               │
│ Deliverable: All PII reliably stripped from extracted data before it touches GPT-4o or the    │
│ database                                                                                      │
│                                                                                               │
│ ---                                                                                           │
│ Phase 5: LLM Analysis Engine (Est. ~1 hr)                                                     │
│                                                                                               │
│ Goal: Build the GPT-4o integration using the structured prompt template from                  │
│ prompt_template.csv. Two-call architecture for extraction verification + financial analysis.  │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Prompt Definitions (backend/prompts/) — each prompt structured per the template schema:    │
│                                                                                               │
│ 1. Prompt 1 — Extraction Verification (prompts/extraction_prompt.py):                         │
│ | Field            | Value                                                                    │
│                                                                                               │
│                                                                                               │
│                |                                                                              │
│ |------------------|------------------------------------------------------------------------- │
│ --------------------------------------------------------------------------------------------- │
│ --------------------------------------------------------------------------------------------- │
│ ---------------|                                                                              │
│ | aiRole           | "Canadian Tax Document Parser"                                           │
│                                                                                               │
│                                                                                               │
│                |                                                                              │
│ | systemRole       | Domain: Canadian tax document analysis. Context: T4/RRSP slip field      │
│ extraction. Audience: Downstream tax analysis engine. Tone: Precise, deterministic.           │
│ Compliance: All PII pre-redacted.                                                             │
│                             |                                                                 │
│ | objective        | A correct output maps every T4 box number to its validated monetary      │
│ value with 2 decimal places, flags uncertain fields as null, and produces zero hallucinated   │
│ values.                                                                                       │
│                     |                                                                         │
│ | taskInstructions | STRICT RULES: Use ONLY data visible in the input. Never infer missing    │
│ values. Return null for unclear fields. STEPS: 1. Read redacted T4 data. 2. Map each box      │
│ number to its value. 3. Validate province as 2-letter code. 4. Flag uncertain fields in       │
│ "uncertain_fields" array. |                                                                   │
│ | taskInput        | Required: redacted_data (object) — T4 box-value pairs with PII removed.  │
│ If missing: return error.                                                                     │
│                                                                                               │
│                |                                                                              │
│ | taskOutputFormat | JSON schema matching T4Fields model                                      │
│                                                                                               │
│                                                                                               │
│                |                                                                              │
│ | taskExample      | NON-NORMATIVE example with synthetic T4 data                             │
│                                                                                               │
│                                                                                               │
│                |                                                                              │
│ | settingsJson     | { "temperature": 0.0, "topP": 1, "max_tokens": 1000, "response_format":  │
│ "json_object" }                                                                               │
│                                                                                               │
│                |                                                                              │
│                                                                                               │
│ 1. Prompt 2 — Financial Analysis (prompts/analysis_prompt.py):                                │
│ | Field            | Value                                                                    │
│                                                                                               │
│                                                                                               │
│          |                                                                                    │
│ |------------------|------------------------------------------------------------------------- │
│ --------------------------------------------------------------------------------------------- │
│ --------------------------------------------------------------------------------------------- │
│ ---------|                                                                                    │
│ | aiRole           | "Canadian Tax Optimization Analyst"                                      │
│                                                                                               │
│                                                                                               │
│          |                                                                                    │
│ | systemRole       | Domain: Canadian personal tax optimization. Context: Analyzing           │
│ anonymized financial data against 20+ strategies. Audience: Licensed financial advisor review │
│  queue. Tone: Factual, evidence-based. Compliance: PIPEDA-compliant, no PII in input.         │
│                   |                                                                           │
│ | objective        | A correct output identifies all applicable tax optimization strategies   │
│ from the 20-item catalog, with dollar estimates backed by shown calculations, sorted by value │
│  descending, at confidence levels reflecting data completeness.                               │
│           |                                                                                   │
│ | taskInstructions | STRICT RULES: Use ONLY provided data. Never invent missing values. Show  │
│ calculation for every estimate. STEPS: 1. Read structured fields + CRA data. 2. Evaluate each │
│  of 20 strategies. 3. Calculate estimated value for applicable ones. 4. Sort by               │
│ estimated_value desc. |                                                                       │
│ | taskInput        | Required: structured_fields, rrsp_room, tfsa_room, province, tax_year.   │
│ Optional: prior_net_income, capital_loss_cf, hbp_balance.                                     │
│                                                                                               │
│           |                                                                                   │
│ | taskOutputFormat | JSON array of insight objects per insight_schema                         │
│                                                                                               │
│                                                                                               │
│          |                                                                                    │
│ | taskExample      | NON-NORMATIVE CCB_STACKING example from Section 9                        │
│                                                                                               │
│                                                                                               │
│          |                                                                                    │
│ | settingsJson     | { "temperature": 0.2, "topP": 0.9, "max_tokens": 4000,                   │
│ "response_format": "json_object" }                                                            │
│                                                                                               │
│                           |                                                                   │
│                                                                                               │
│ 1. Prompt 3 — Vision OCR (prompts/vision_prompt.py):                                          │
│ | Field            | Value                                                                    │
│                                                                                               │
│                                              |                                                │
│ |------------------|------------------------------------------------------------------------- │
│ --------------------------------------------------------------------------------------------- │
│ ---------------------------------------------|                                                │
│ | aiRole           | "Tax Document OCR Specialist"                                            │
│                                                                                               │
│                                              |                                                │
│ | systemRole       | Domain: Optical character recognition for Canadian tax forms. Context:   │
│ Scanned T4/RRSP images. Audience: Extraction pipeline. Tone: Precise. Compliance: Do not      │
│ extract PII (name, SIN, address).                 |                                           │
│ | objective        | A correct output extracts all T4 box numbers and their monetary values   │
│ from the document image as a clean JSON object, excluding all personal identifiers.           │
│                                               |                                               │
│ | taskInstructions | STRICT RULES: Extract ONLY box numbers and values. Never include         │
│ employee name, SIN, or address. STEPS: 1. Identify document type. 2. Extract box-value pairs. │
│  3. Include employer_name, province_code, tax_year. |                                         │
│ | taskInput        | Required: base64-encoded image of T4/RRSP document.                      │
│                                                                                               │
│                                              |                                                │
│ | taskOutputFormat | { "14": "float", "16": "float", ..., "employer_name": "string",          │
│ "province_code": "string", "tax_year": "integer" }                                            │
│                                                      |                                        │
│ | settingsJson     | { "temperature": 0.0, "topP": 1, "max_tokens": 1000, "response_format":  │
│ "json_object" }                                                                               │
│                                              |                                                │
│                                                                                               │
│ 2. LLM Service (services/llm_service.py):                                                     │
│   - verify_extraction(redacted_data) — Call 1 using extraction_prompt                         │
│   - analyze_financials(structured_fields, cra_data) — Call 2 using analysis_prompt            │
│   - extract_via_vision(image_base64) — Vision call using vision_prompt                        │
│   - Prompt builder function: assembles OpenAI messages from template fields (system message   │
│ from aiRole+systemRole, user message from taskInstructions+taskInput+data)                    │
│   - Response parsing and JSON validation                                                      │
│   - Error handling, retry logic (max 2 retries), token management                             │
│   - Settings applied from each prompt's settingsJson                                          │
│ 3. Analysis Router (routers/analysis.py):                                                     │
│   - POST /api/analyze/{profile_id} — trigger full analysis pipeline                           │
│   - GET /api/analysis/{profile_id}/status — check analysis progress                           │
│   - GET /api/analysis/{profile_id}/results — get results                                      │
│                                                                                               │
│ Deliverable: End-to-end flow from redacted T4 data → GPT-4o (with properly structured         │
│ prompts) → structured insights JSON                                                           │
│                                                                                               │
│ ---                                                                                           │
│ Phase 6: Benefit Engine & Insight Generation (Est. ~45 min)                                   │
│                                                                                               │
│ Goal: Build the customer benefit engine — prioritize, format, and categorize all identified   │
│ optimizations.                                                                                │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Benefit Engine (services/benefit_engine.py):                                               │
│   - generate_insights(profile, llm_results) — combine LLM output with deterministic tax       │
│ engine calculations                                                                           │
│   - Priority assignment: HIGH/MEDIUM/LOW based on estimated value + time-sensitivity          │
│   - Category assignment: ACT_NOW / THIS_YEAR / LONG_TERM                                      │
│   - All 20 insight types with trigger conditions (from Section 9 catalog)                     │
│   - Value estimation with calculation shown                                                   │
│   - Action required + product link mapping (wealthsimple://rrsp, tfsa, fhsa, tax)             │
│   - Summary generation: total savings, counts by category, overall confidence                 │
│ 2. Reconciliation Service (services/reconciliation.py):                                       │
│   - reconcile(cra_data, upload_data) — merge CRA + upload sources                             │
│   - Match T4s by employer payroll account number                                              │
│   - Flag discrepancies > $0.01                                                                │
│   - Current-year upload priority, prior-year CRA priority                                     │
│   - Multi-employer aggregation for overpayment calculations                                   │
│ 3. Unified Financial Profile builder — populate the full schema from Section 12               │
│                                                                                               │
│ Deliverable: Given a T4 upload, produce a complete prioritized insights report with dollar    │
│ values and plain-English explanations                                                         │
│                                                                                               │
│ ---                                                                                           │
│ Phase 7: Human Review Layer (Est. ~45 min)                                                    │
│                                                                                               │
│ Goal: Build the advisor review queue — the architectural boundary ensuring no recommendation  │
│ reaches customers without human sign-off.                                                     │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Advisor Router (routers/advisor.py):                                                       │
│   - GET /api/advisor/queue — list pending review cases (paginated, sorted by SLA)             │
│   - GET /api/advisor/case/{case_id} — full case detail with insights and confidence scores    │
│   - POST /api/advisor/case/{case_id}/approve — approve all or individual insights             │
│   - POST /api/advisor/case/{case_id}/reject — reject with reason                              │
│   - POST /api/advisor/case/{case_id}/modify — modify insight before approval                  │
│   - POST /api/advisor/case/{case_id}/escalate — escalate to senior advisor                    │
│ 2. Review Rules Engine:                                                                       │
│   - Auto-approve criteria: confidence >= 0.85, no validation flags, no anomaly flags, value < │
│  $50K                                                                                         │
│   - Mandatory human review triggers: TAX_RATE_ANOMALY, INCOME_DISCREPANCY,                    │
│ CPP_EXCEEDS_MAXIMUM, HIGH_VALUE_INSIGHT, NEAR_RETIREMENT, MULTI_EMPLOYER_COMPLEX              │
│ 3. Audit Service (services/audit_service.py):                                                 │
│   - Log every data access with timestamp, user_id, purpose                                    │
│   - Immutable audit trail (PIPEDA compliance)                                                 │
│   - Review decision logging                                                                   │
│                                                                                               │
│ Deliverable: Advisor can view queue, review cases, approve/reject/modify insights — full      │
│ audit trail                                                                                   │
│                                                                                               │
│ ---                                                                                           │
│ Phase 8: React Frontend — Upload & Analysis UI (Est. ~1 hr)                                   │
│                                                                                               │
│ Goal: Build the customer-facing upload interface and analysis results view.                   │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Upload Page (pages/Upload.jsx):                                                            │
│   - Drag-and-drop document upload (PDF/image)                                                 │
│   - File preview and validation                                                               │
│   - Upload progress indicator                                                                 │
│   - CRA authorization flow placeholder (button linking to CRA auth)                           │
│ 2. DocumentUploader Component (components/DocumentUploader.jsx):                              │
│   - Drag-and-drop zone with file type validation                                              │
│   - Size limit check (10MB)                                                                   │
│   - Preview thumbnail for uploaded document                                                   │
│ 3. Analysis Page (pages/Analysis.jsx):                                                        │
│   - Processing progress indicator (extraction → redaction → analysis → insights)              │
│   - Step-by-step status updates                                                               │
│ 4. Insights Page (pages/Insights.jsx):                                                        │
│   - Personalized savings summary (total identified savings)                                   │
│   - InsightCard components categorized by ACT_NOW / THIS_YEAR / LONG_TERM                     │
│   - Color coding: red (ACT NOW), yellow (THIS YEAR), green (LONG TERM)                        │
│   - Action buttons linking to Wealthsimple products                                           │
│   - Download PDF option                                                                       │
│ 5. InsightCard Component (components/InsightCard.jsx) — headline, detail, estimated value,    │
│ action button                                                                                 │
│ 6. SavingsSummary Component (components/SavingsSummary.jsx) — total savings, breakdown by     │
│ category                                                                                      │
│ 7. API Service (services/api.js) — all backend API calls                                      │
│                                                                                               │
│ Deliverable: Complete customer flow — upload document → see processing → view prioritized     │
│ insights                                                                                      │
│                                                                                               │
│ ---                                                                                           │
│ Phase 9: React Frontend — Advisor Dashboard (Est. ~45 min)                                    │
│                                                                                               │
│ Goal: Build the licensed advisor review interface.                                            │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. AdvisorDashboard Page (pages/AdvisorDashboard.jsx):                                        │
│   - Queue view: pending cases with confidence scores, SLA countdown                           │
│   - Filter/sort by: confidence, priority, province, flags                                     │
│   - Stats: total pending, avg SLA remaining, auto-approved count                              │
│ 2. ReviewQueue Component (components/ReviewQueue.jsx):                                        │
│   - Case list with summary info (income, province, insight count, confidence)                 │
│   - Flag indicators for anomalies                                                             │
│   - Color-coded confidence bars                                                               │
│ 3. CaseDetail Component (components/CaseDetail.jsx):                                          │
│   - Full insight list with AI analysis + confidence per insight                               │
│   - One-click: Approve All / Review Individual / Escalate / Reject                            │
│   - Modification interface (edit insight text/values before approval)                         │
│   - Original document access (on explicit request only — PII gated)                           │
│   - Full audit trail view                                                                     │
│                                                                                               │
│ Deliverable: Working advisor dashboard — view queue, drill into cases, approve/modify/reject, │
│  full audit                                                                                   │
│                                                                                               │
│ ---                                                                                           │
│ Phase 10: Integration Testing & Demo Prep (Est. ~45 min)                                      │
│                                                                                               │
│ Goal: End-to-end testing, demo scenarios, and submission preparation.                         │
│                                                                                               │
│ Tasks:                                                                                        │
│                                                                                               │
│ 1. Create 3 synthetic T4 test scenarios:                                                      │
│   - Scenario A: Single employer, Ontario, $85K income — triggers RRSP optimization,           │
│ over-withholding, TFSA gap                                                                    │
│   - Scenario B: Multi-employer, BC, $142K income — triggers CPP overpayment, bracket          │
│ straddling, FHSA eligibility                                                                  │
│   - Scenario C: Union worker with children, QC, $94K family income — triggers CCB stacking,   │
│ union dues GST rebate, spousal RRSP                                                           │
│ 2. End-to-end test: Upload → Extract → Redact → Analyze → Insights → Advisor Review → Approve │
│  → Customer Delivery                                                                          │
│ 3. Fix any integration issues between backend and frontend                                    │
│ 4. Polish UI — clean layout, consistent styling, responsive design                            │
│ 5. Prepare demo flow — the best scenario for a 2-3 minute demo video                          │
│                                                                                               │
│ Deliverable: Fully working demo with 3 realistic scenarios, ready for submission              │
│                                                                                               │
│ ---                                                                                           │
│ Verification Plan                                                                             │
│                                                                                               │
│ 1. Phase 1: uvicorn main:app --reload starts without errors, React npm run dev shows default  │
│ page                                                                                          │
│ 2. Phase 2: Unit test tax_engine with known inputs — verify Ontario $85K income produces      │
│ correct marginal rate (43.41%) and liability (~$18,432)                                       │
│ 3. Phase 3: Upload a sample T4 PDF to /api/upload, verify JSON output matches expected box    │
│ values                                                                                        │
│ 4. Phase 4: Pass sample text with SIN, address, DOB through redaction — verify all PII        │
│ removed, financial figures preserved                                                          │
│ 5. Phase 5: Hit /api/analyze/{id} with sample profile, verify GPT-4o returns valid structured │
│  insights                                                                                     │
│ 6. Phase 6: Verify benefit engine produces all applicable insights for each test scenario     │
│ with correct dollar values                                                                    │
│ 7. Phase 7: Verify advisor can view queue, approve case, and approved insights become visible │
│  in customer report                                                                           │
│ 8. Phase 8-9: Manual UI walkthrough — upload, processing animation, insight cards display,    │
│ advisor queue works                                                                           │
│ 9. Phase 10: Full end-to-end with all 3 test scenarios passing cleanly                        │
│                                                                                               │
│ ---                                                                                           │
│ Key Files Summary                                                                             │
│                                                                                               │
│ ┌───────────────────────────────────────┬───────────────────────────────────────────────────┐ │
│ │                 File                  │                      Purpose                      │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/main.py                       │ FastAPI entry point, CORS, DB init                │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/ocr_service.py       │ PDF/image extraction pipeline                     │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/redaction_service.py │ PII masking (deterministic regex)                 │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/prompts/*.py                  │ Structured LLM prompts (per prompt_template.csv   │ │
│ │                                       │ schema)                                           │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/llm_service.py       │ GPT-4o integration (2-call architecture)          │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/tax_engine.py        │ Canadian tax rules (deterministic)                │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/benefit_engine.py    │ Insight generation & prioritization               │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/reconciliation.py    │ CRA + upload data merger                          │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/services/audit_service.py     │ PIPEDA-compliant audit logging                    │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/rules/*.py                    │ Tax brackets, limits, rates (all 13 provinces)    │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ backend/database/models.py            │ SQLAlchemy ORM (profiles, insights, cases, audit) │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ frontend/pages/Upload.jsx             │ Customer document upload                          │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ frontend/pages/Insights.jsx           │ Customer insight report                           │ │
│ ├───────────────────────────────────────┼───────────────────────────────────────────────────┤ │
│ │ frontend/pages/AdvisorDashboard.jsx   │ Advisor review queue                              │ │
│ └───────────────────────────────────────┴───────────────────────────────────────────────────┘ │
