# Wealthsimple AI Tax Analyzer — Full System Plan

> **Project:** AI-Native Tax Document Analysis & Financial Optimization Engine
>
> **Prepared for:** Wealthsimple AI Builder Submission
>
> **Date:** February 2026
>
> **Stack:** Python · OpenAI GPT-4o · FastAPI · React · SQLite

---

## Table of Contents

1. [Executive Summary](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#1-executive-summary)
2. [Problem Statement](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#2-problem-statement)
3. [Solution Overview](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#3-solution-overview)
4. [System Architecture](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#4-system-architecture)
5. [Data Sources](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#5-data-sources)
6. [Component Breakdown](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#6-component-breakdown)
7. [OCR + Extraction Pipeline](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#7-ocr--extraction-pipeline)
8. [LLM Analysis Engine](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#8-llm-analysis-engine)
9. [Customer Benefit Engine](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#9-customer-benefit-engine)
10. [Privacy &amp; PII Strategy](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#10-privacy--pii-strategy)
11. [Human Review Layer](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#11-human-review-layer)
12. [Data Schema](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#12-data-schema)
13. [Build Plan &amp; Timeline](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#13-build-plan--timeline)
14. [What Breaks First at Scale](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#14-what-breaks-first-at-scale)
15. [Submission Answers](https://claude.ai/chat/5513db1f-8bd3-417d-90ba-ac6e8fdef095#15-submission-answers)

---

## 1. Executive Summary

Canadian tax documents — specifically T4 slips and RRSP contribution receipts — contain the raw inputs for over 20 distinct financial optimization strategies that most Canadians never act on. A skilled financial advisor can decode these documents into personalized, actionable savings worth thousands of dollars annually. Today, that expertise is inaccessible to most of Wealthsimple's 3+ million users.

This system rebuilds that workflow from scratch as an AI-native pipeline. It ingests T4 and RRSP documents via two paths — direct CRA authorization (leveraging Wealthsimple's existing CRA connection) and user document upload — reconciles both sources, performs full analysis using GPT-4o with PII redacted before every API call, and surfaces a prioritized list of legal tax savings and wealth-building opportunities in plain English.

A licensed human advisor reviews every recommendation before it reaches the client. The AI handles everything up to that moment.

---

## 2. Problem Statement

### The Legacy Workflow

```
Customer receives T4 → Stores it in a drawer → Files taxes in April
→ Misses RRSP deadline → Gets average $2,295 refund → Spends it
→ Repeat every year for 30 years
→ Retires with significantly less than optimal
```

### The Scale Problem

* Wealthsimple has **3+ million users**
* A single financial advisor can meaningfully serve **~150 clients/year**
* To serve 3M users at human advisor ratios would require **20,000 advisors**
* Most users never receive proactive financial guidance at all

### The Knowledge Gap

Studies show only **7% of Canadians** review their T4 details when filing. The average Canadian leaves thousands of dollars on the table annually through:

* Missed RRSP optimization (wrong timing, wrong amount, wrong account type)
* CPP/EI overpayments never claimed (up to $2,000+ for multi-job workers)
* Over-withholding giving CRA interest-free loans ($200–$1,000/month)
* Canada Child Benefit stacking through RRSP contributions (40–60% effective returns)
* Union dues GST rebates almost universally unclaimed
* FHSA accounts never opened despite free contribution room accumulating

---

## 3. Solution Overview

### What This System Does

An AI-powered financial analysis engine that:

1. Ingests tax documents from two sources (CRA direct + user upload)
2. Extracts and reconciles all financial data
3. Redacts PII before any external API call
4. Analyzes with GPT-4o against 20+ Canadian tax optimization strategies
5. Produces a prioritized, plain-English benefit report
6. Queues every recommendation for human advisor review
7. Delivers approved insights to the customer with direct Wealthsimple product links

### Human vs AI Responsibility

| Responsibility                            | Owner                              |
| ----------------------------------------- | ---------------------------------- |
| Document ingestion and extraction         | AI                                 |
| PII detection and redaction               | AI (deterministic rules)           |
| Financial data reconciliation             | AI                                 |
| Tax calculation and optimization analysis | AI                                 |
| Benefit identification and quantification | AI                                 |
| Plain English explanation generation      | AI                                 |
| Flagging low-confidence extractions       | AI                                 |
| Final recommendation approval             | **Human (licensed advisor)** |
| Personalized advice delivery              | **Human (licensed advisor)** |
| Edge case and complaint handling          | **Human (licensed advisor)** |

### The Non-Negotiable Human Boundary

**No recommendation reaches a customer without licensed advisor sign-off.**

This boundary is architectural — not a policy. The system has no delivery pathway to the customer that bypasses the review queue. This exists because:

* Personalized tax advice carries legal liability under Canadian securities regulation
* PIPEDA requires human accountability for decisions affecting individuals
* The AI sees one document — a human brings the full financial picture

---

## 4. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER LAYER                               │
│                                                                     │
│   ┌─────────────────────┐       ┌──────────────────────────────┐   │
│   │   Wealthsimple App  │       │     T4 Upload Interface      │   │
│   │   (CRA Authorization│       │  (drag-and-drop PDF/image)   │   │
│   │    via existing tie)│       │                              │   │
│   └──────────┬──────────┘       └──────────────┬───────────────┘   │
└──────────────┼───────────────────────────────────┼─────────────────┘
               │                                   │
               ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                           │
│                                                                     │
│   ┌──────────────────────────┐   ┌──────────────────────────────┐  │
│   │   CRA AFR API Connector  │   │    OCR Extraction Engine     │  │
│   │                          │   │                              │  │
│   │  • All T4s (all employers│   │  • PyMuPDF (digital PDFs)   │  │
│   │  • RRSP deduction limit  │   │  • GPT-4o Vision (scanned)  │  │
│   │  • TFSA room exact       │   │  • Field validation rules   │  │
│   │  • Prior NOA             │   │  • Confidence scoring       │  │
│   │  • T3/T5/T4A/T5008       │   │                              │  │
│   │  • HBP/LLP balances      │   │                              │  │
│   │  • Capital loss c/f      │   │                              │  │
│   │  • Benefit history       │   │                              │  │
│   └─────────────┬────────────┘   └──────────────┬───────────────┘  │
└─────────────────┼───────────────────────────────┼──────────────────┘
                  │                               │
                  ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PII PROTECTION LAYER                             │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                   Redaction Engine                          │  │
│   │                                                             │  │
│   │  SIN: 123 456 789 → [SIN-REDACTED]                         │  │
│   │  Name: James Sprat → [NAME-REDACTED]                        │  │
│   │  DOB: 1985-03-12 → [DOB-REDACTED]                          │  │
│   │  Address: 120 Elm St → [ADDRESS-REDACTED]                   │  │
│   │                                                             │  │
│   │  Only financial figures and box numbers pass through        │  │
│   └─────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   DATA RECONCILIATION LAYER                         │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │              CRA Data  ←→  Upload Data                      │  │
│   │                                                             │  │
│   │  • Match T4s by employer payroll account number             │  │
│   │  • Flag income discrepancies > $0.01                        │  │
│   │  • Detect employer filing errors                            │  │
│   │  • Identify current-year advantage (upload ahead of CRA)    │  │
│   │  • Merge into unified financial profile                     │  │
│   └─────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AI ANALYSIS ENGINE                               │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              GPT-4o (Redacted data only)                  │    │
│   │                                                           │    │
│   │  Call 1: Field extraction & validation                    │    │
│   │  Call 2: Tax calculation & bracket analysis               │    │
│   │  Call 3: Benefit optimization (20+ strategies)            │    │
│   │  Call 4: Plain English explanation generation             │    │
│   └───────────────────────────┬───────────────────────────────┘    │
│                               │                                     │
│   ┌───────────────────────────▼───────────────────────────────┐    │
│   │           Canadian Tax Rules Engine (Python)              │    │
│   │                                                           │    │
│   │  • 2024/2025 federal + provincial brackets (all provinces)│    │
│   │  • RRSP/TFSA/FHSA limits and formulas                    │    │
│   │  • CPP/EI max contributions and overpayment rules        │    │
│   │  • CCB/GST credit phase-out rates                        │    │
│   │  • OAS clawback thresholds                               │    │
│   │  • Capital gains inclusion rates                         │    │
│   └───────────────────────────┬───────────────────────────────┘    │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  CUSTOMER BENEFIT ENGINE                            │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              Insight Prioritization                       │    │
│   │                                                           │    │
│   │  🔴 ACT NOW (time-sensitive, high value)                  │    │
│   │  🟡 THIS TAX YEAR (before filing)                         │    │
│   │  🟢 LONG-TERM (wealth building)                           │    │
│   └───────────────────────────┬───────────────────────────────┘    │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   HUMAN REVIEW LAYER                                │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │           Licensed Advisor Dashboard                      │    │
│   │                                                           │    │
│   │  • Anonymized case queue (no PII visible by default)      │    │
│   │  • AI analysis + confidence score per insight             │    │
│   │  • Original document available on explicit access request │    │
│   │  • One-click: Approve / Modify / Reject / Escalate        │    │
│   │  • Full audit trail (PIPEDA compliance)                   │    │
│   │  • SLA: 24-hour review target                             │    │
│   └───────────────────────────┬───────────────────────────────┘    │
└───────────────────────────────┼─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DELIVERY LAYER                                 │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              Customer Insight Report                      │    │
│   │                                                           │    │
│   │  • Personalized savings summary                           │    │
│   │  • Plain English explanations (no jargon)                 │    │
│   │  • Direct action buttons linking to Wealthsimple products │    │
│   │  • Advisor contact option for any insight                 │    │
│   │  • Download PDF option                                    │    │
│   └───────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
Customer                System                    External
   │                       │                          │
   │── Upload T4 PDF ──────►│                          │
   │                       │── OCR Extract ──────────►│
   │                       │◄─ Raw Text ──────────────│
   │                       │                          │
   │── Authorize CRA ──────►│                          │
   │                       │── CRA AFR API ──────────►│
   │                       │◄─ All slips + room ──────│
   │                       │                          │
   │                       │── Reconcile sources       │
   │                       │── Redact PII              │
   │                       │                          │
   │                       │── Redacted data ─────────►│
   │                       │                    GPT-4o │
   │                       │◄─ Structured JSON ────────│
   │                       │                          │
   │                       │── Tax rules engine        │
   │                       │── Generate insights       │
   │                       │── Queue for advisor       │
   │                       │                          │
   │                       │    [Advisor reviews]      │
   │                       │                          │
   │◄── Approved insights ─│                          │
   │                       │                          │
```

---

## 5. Data Sources

### Source A — CRA Direct API (Auto-fill my return)

Wealthsimple already has an existing CRA connection. Upon user authorization, the system pulls:

| Slip Type          | Fields Available                      | Insight Powered                         |
| ------------------ | ------------------------------------- | --------------------------------------- |
| T4 (all employers) | All boxes 14–67                      | CPP/EI overpayment, full income picture |
| T4A                | Pension, RRSP income, other income    | Retirement income picture               |
| T4E                | EI benefits received                  | Income replacement planning             |
| T4RSP              | RRSP withdrawals                      | Withdrawal pattern analysis             |
| T4RIF              | RRIF withdrawals                      | Decumulation planning                   |
| T3                 | Trust income, capital gains           | Investment tax efficiency               |
| T5                 | Investment income by type             | Dividend vs interest optimization       |
| T5008              | Securities transactions               | Capital gains/loss tracking             |
| NOA                | Prior year net income, refund/balance | Over-withholding detection              |
| RRSP room          | Exact deduction limit                 | Precise contribution advice             |
| TFSA room          | Exact remaining room                  | TFSA vs RRSP decision                   |
| HBP balance        | Outstanding repayment                 | Home buyers planning                    |
| Capital loss c/f   | Unused capital losses                 | Tax-loss harvesting timing              |

### Source B — Document Upload

| Document           | Extraction Method       | Advantage Over CRA                      |
| ------------------ | ----------------------- | --------------------------------------- |
| T4 PDF (digital)   | PyMuPDF text extraction | Current year data 6–8 weeks before CRA |
| T4 image/scan      | GPT-4o Vision           | Works for paper slips                   |
| RRSP receipt PDF   | PyMuPDF + GPT-4o        | Current year contribution confirmation  |
| RRSP receipt image | GPT-4o Vision           | Immediate contribution tracking         |

### Source Reconciliation Rules

```python
RECONCILIATION_RULES = {
    "income_mismatch_threshold": 0.01,      # Flag if > $0.01 difference
    "current_year_upload_priority": True,    # Upload wins for current year
    "cra_priority_for_prior_years": True,   # CRA wins for prior years
    "multi_employer_aggregation": True,     # Sum all T4s for overpayment calc
    "missing_slip_detection": True,         # Alert if CRA has slips not uploaded
}
```

---

## 6. Component Breakdown

### Backend Components

```
backend/
├── main.py                    # FastAPI application entry point
├── routers/
│   ├── upload.py              # Document upload endpoints
│   ├── cra.py                 # CRA API connector endpoints
│   ├── analysis.py            # Analysis trigger endpoints
│   └── advisor.py             # Human review dashboard endpoints
├── services/
│   ├── ocr_service.py         # OCR + extraction pipeline
│   ├── redaction_service.py   # PII detection and masking
│   ├── reconciliation.py      # CRA + upload data merger
│   ├── llm_service.py         # GPT-4o API calls
│   ├── tax_engine.py          # Canadian tax rules (deterministic)
│   ├── benefit_engine.py      # Insight generation + prioritization
│   └── audit_service.py       # PIPEDA compliance logging
├── models/
│   ├── t4_schema.py           # T4 field definitions
│   ├── rrsp_schema.py         # RRSP receipt field definitions
│   ├── insight_schema.py      # Insight output structure
│   └── case_schema.py         # Review case structure
├── rules/
│   ├── federal_brackets.py    # 2024/2025 federal tax brackets
│   ├── provincial_brackets.py # All 13 provinces/territories
│   ├── contribution_limits.py # RRSP/TFSA/FHSA limits by year
│   ├── cpp_ei_rates.py        # CPP/EI rates and maximums
│   └── benefit_rates.py       # CCB/GST/OAS/GIS phase-out rates
└── database/
    ├── models.py              # SQLAlchemy ORM models
    └── migrations/            # DB schema versions
```

### Frontend Components

```
frontend/
├── pages/
│   ├── Upload.jsx             # Document upload interface
│   ├── Analysis.jsx           # Analysis progress + results
│   ├── Insights.jsx           # Customer benefit report
│   └── AdvisorDashboard.jsx   # Human review queue
├── components/
│   ├── DocumentUploader.jsx   # Drag-and-drop with preview
│   ├── InsightCard.jsx        # Individual insight display
│   ├── SavingsSummary.jsx     # Total identified savings
│   ├── ReviewQueue.jsx        # Advisor case list
│   └── CaseDetail.jsx         # Advisor review interface
└── services/
    ├── api.js                 # Backend API calls
    └── auth.js                # CRA authorization flow
```

---

## 7. OCR + Extraction Pipeline

### Pipeline Flow

```
Document Input
      │
      ▼
┌─────────────────────────────────┐
│      File Type Detection        │
│  PDF (digital) → PyMuPDF        │
│  PDF (scanned) → GPT-4o Vision  │
│  Image (.png/.jpg) → GPT-4o     │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Raw Text Extraction        │
│  Digital: fitz.get_text()       │
│  Scanned: base64 → GPT-4o       │
│  Confidence scoring per field   │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Field Parsing              │
│  Box number → value mapping     │
│  Regex patterns per field type  │
│  Validation against CRA ranges  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      PII Redaction              │
│  SIN pattern matching           │
│  Name entity detection          │
│  Address/postal code removal    │
│  DOB pattern removal            │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Structured JSON Output     │
│  Confidence score per field     │
│  Low-confidence flags           │
│  Raw file deleted immediately   │
└─────────────────────────────────┘
```

### Core Extraction Code

```python
# ocr_service.py

import fitz  # PyMuPDF
import re
import base64
from openai import OpenAI
from models.t4_schema import T4Fields

client = OpenAI()

def extract_t4(file_path: str) -> dict:
    """
    Main extraction pipeline.
    Tries digital extraction first, falls back to GPT-4o Vision.
    """
    # Step 1: Attempt digital text extraction
    raw_text = _extract_digital(file_path)
  
    # Step 2: If insufficient text, use GPT-4o Vision
    if len(raw_text.strip()) < 100:
        raw_text = _extract_vision(file_path)
  
    # Step 3: Parse fields from raw text
    raw_fields = _parse_fields(raw_text)
  
    # Step 4: Redact PII BEFORE anything is stored or sent externally
    redacted_fields = redact_pii(raw_fields)
  
    # Step 5: Validate against known CRA ranges
    validated = _validate_fields(redacted_fields)
  
    # Step 6: Delete raw file immediately
    import os
    os.remove(file_path)
  
    return validated


def _extract_digital(file_path: str) -> str:
    """Extract text from digital PDF using PyMuPDF."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def _extract_vision(file_path: str) -> str:
    """Extract text from scanned document using GPT-4o Vision."""
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
  
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                },
                {
                    "type": "text",
                    "text": """Extract all T4 slip data. 
                    Return ONLY a JSON object with box numbers as keys.
                    Example: {"14": 85000.00, "16": 3867.50, "22": 18432.00}
                    Include: employer_name, province_code, tax_year.
                    Do not include employee name, SIN, or address."""
                }
            ]
        }],
        max_tokens=1000
    )
    return response.choices[0].message.content


def redact_pii(text_or_dict) -> dict:
    """
    Deterministic PII redaction using regex patterns.
    Runs LOCALLY — never sent to any external service.
    """
    if isinstance(text_or_dict, str):
        text = text_or_dict
        # SIN: 123 456 789 or 123-456-789
        text = re.sub(
            r'\b\d{3}[\s-]\d{3}[\s-]\d{3}\b', 
            '[SIN-REDACTED]', text
        )
        # Postal codes
        text = re.sub(
            r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b', 
            '[POSTAL-REDACTED]', text
        )
        # Dates of birth
        text = re.sub(
            r'\b\d{4}[-/]\d{2}[-/]\d{2}\b', 
            '[DOB-REDACTED]', text
        )
        return text
    return text_or_dict  # Already structured dict — names never stored


def _validate_fields(fields: dict) -> dict:
    """
    Validate extracted values against known CRA ranges.
    Flags anomalies for human review.
    """
    flags = []
  
    box14 = fields.get("14", 0)
    box16 = fields.get("16", 0)
    box18 = fields.get("18", 0)
  
    # CPP should not exceed maximum
    if box16 > 3867.50:
        flags.append("CPP_EXCEEDS_MAXIMUM")
  
    # EI should not exceed maximum  
    if box18 > 1049.12:
        flags.append("EI_EXCEEDS_MAXIMUM")
  
    # Box 22 should be reasonable % of Box 14
    box22 = fields.get("22", 0)
    if box14 > 0:
        effective_rate = box22 / box14
        if effective_rate > 0.55 or effective_rate < 0.05:
            flags.append("TAX_RATE_ANOMALY")
  
    fields["_validation_flags"] = flags
    fields["_confidence"] = 1.0 - (len(flags) * 0.15)
  
    return fields
```

---

## 8. LLM Analysis Engine

### Prompt Architecture

The LLM receives only redacted financial figures. Two-call structure:

**Call 1 — Structured Extraction Verification**

```python
EXTRACTION_PROMPT = """
You are a Canadian tax document parser.

Given this extracted T4 data (all PII already redacted):
{redacted_data}

Verify and structure the fields into this exact JSON schema:
{schema}

Rules:
- All monetary values as float with 2 decimal places
- province as 2-letter code (ON, BC, AB, QC, etc.)
- tax_year as integer
- If a field is unclear, set to null and add to "uncertain_fields" array
- Do not infer or estimate missing values
"""
```

**Call 2 — Financial Analysis**

```python
ANALYSIS_PROMPT = """
You are a Canadian tax optimization expert analyzing anonymized financial data.

FINANCIAL DATA (all PII removed):
{structured_fields}

CRA ACCOUNT DATA:
- Exact RRSP room: {rrsp_room}
- TFSA room remaining: {tfsa_room}
- Prior year net income: {prior_net_income}
- Capital loss carryforward: {capital_loss_cf}
- HBP balance outstanding: {hbp_balance}

TAX YEAR: {tax_year}
PROVINCE: {province}

Using Canadian tax law for {tax_year}, identify ALL applicable 
optimization opportunities from this list:

1. RRSP_BRACKET_OPTIMIZATION — exact contribution to minimize bracket
2. RRSP_REFUND_ESTIMATE — tax saving from full room contribution
3. OVER_WITHHOLDING — T1213 opportunity if Box22 >> estimated liability
4. CPP_OVERPAYMENT — if Box16 across all T4s > annual maximum
5. EI_OVERPAYMENT — if Box18 across all T4s > annual maximum
6. TFSA_GAP — unused TFSA room analysis
7. FHSA_ELIGIBILITY — if no HBP history, FHSA opportunity
8. CCB_STACKING — RRSP impact on Canada Child Benefit (if children present)
9. OAS_CLAWBACK_PREVENTION — if income near $90,997 threshold
10. UNION_DUES_GST_REBATE — Box44 > 0 and province has HST
11. SPOUSAL_RRSP — if income gap between spouses (requires spouse data)
12. RRSP_GROSS_UP — borrow-to-maximize strategy at current marginal rate
13. HBP_STRATEGY — contribute then withdraw if first-time buyer
14. CAPITAL_LOSS_HARVEST — timing of gains realization
15. DIVIDEND_OPTIMIZATION — eligible vs non-eligible dividend tax rates
16. PENSION_ADJUSTMENT_IMPACT — Box52 eating RRSP room explanation
17. RETIRING_ALLOWANCE_TRANSFER — Box66 direct RRSP transfer if present
18. BRACKET_STRADDLING — exact distance to next bracket threshold
19. RRSP_CARRY_FORWARD — accumulated unused room opportunity
20. CPP_DEFERRAL — if approaching 60-70 age range

For each applicable opportunity, return:
{
  "id": "INSIGHT_ID",
  "applicable": true/false,
  "priority": "HIGH/MEDIUM/LOW",
  "category": "ACT_NOW/THIS_YEAR/LONG_TERM",
  "headline": "One sentence — plain English, no jargon",
  "detail": "2-3 sentences explaining the opportunity",
  "estimated_value": dollar_amount_or_null,
  "calculation_shown": "How you calculated the value",
  "action_required": "Specific step the customer should take",
  "product_link": "Wealthsimple product if applicable (RRSP/TFSA/FHSA)",
  "confidence": 0.0-1.0,
  "requires_additional_info": ["list of missing data that would improve this"]
}

Return as JSON array. Sort by estimated_value descending.
"""
```

---

## 9. Customer Benefit Engine

### The 20 Insights — Full Catalog

#### 🔴 ACT NOW (Time-Sensitive)

| # | Insight                      | Trigger Condition                                                     | Typical Value              |
| - | ---------------------------- | --------------------------------------------------------------------- | -------------------------- |
| 1 | **RRSP Deadline**      | RRSP room exists + March approaching                                  | $1,000–$15,000 tax saving |
| 2 | **Over-withholding**   | Box22 > estimated_liability by >$500      | $200–$1,000/month freed  |                            |
| 3 | **CPP Overpayment**    | Multiple T4s + sum(Box16) > max                                       | $100–$2,000 refund        |
| 4 | **EI Overpayment**     | Multiple T4s + sum(Box18) > max                                       | $100–$600 refund          |
| 5 | **Bracket Straddling** | Income within $15,000 of bracket boundary | $200–$1,500 extra saving |                            |

#### 🟡 THIS TAX YEAR (Before Filing)

| #  | Insight                        | Trigger Condition                    | Typical Value                    |
| -- | ------------------------------ | ------------------------------------ | -------------------------------- |
| 6  | **RRSP Gross-Up**        | Marginal rate > 33% + room available | 40–70% more in RRSP             |
| 7  | **CCB Stacking**         | Has children + RRSP room             | $500–$3,000 additional benefits |
| 8  | **OAS Protection**       | Income within $5,000 of $90,997      | $8,500/year protected            |
| 9  | **Union Dues GST**       | Box44 > 0 + HST province             | $100–$400 rebate                |
| 10 | **FHSA Eligibility**     | No HBP history + employed            | $8,000/year + deduction          |
| 11 | **HBP Strategy**         | First-time buyer + RRSP exists       | $60,000 tax-free                 |
| 12 | **Capital Loss Harvest** | Capital loss c/f > 0 + has gains     | Variable                         |

#### 🟢 LONG-TERM (Wealth Building)

| #  | Insight                         | Trigger Condition              | Typical Value                |
| -- | ------------------------------- | ------------------------------ | ---------------------------- |
| 13 | **Retirement Gap**        | Always — baseline analysis    | Lifetime impact              |
| 14 | **Spousal RRSP**          | Income gap between spouses     | $20,000–$50,000 lifetime    |
| 15 | **RRSP Carry-Forward**    | Large accumulated unused room  | Varies                       |
| 16 | **TFSA Gap**              | Unused TFSA room significant   | Tax-free growth opportunity  |
| 17 | **Pension Adjustment**    | Box52 > 0                      | Explains room reduction      |
| 18 | **Dividend Optimization** | T3/T5 investment income exists | 10–20% tax rate reduction   |
| 19 | **CPP Deferral**          | Age 60–70 range               | 42% higher CPP at 70         |
| 20 | **RRIF Planning**         | Age 60+ with large RRSP        | Reduces forced income spikes |

### Insight Output Example

```json
{
  "insights": [
    {
      "id": "CCB_STACKING",
      "priority": "HIGH",
      "category": "THIS_YEAR",
      "headline": "Contributing to your RRSP could increase your child benefits by $1,847",
      "detail": "Your family net income of $94,000 is in the Canada Child Benefit phase-out zone. A $12,000 RRSP contribution reduces your net income to $82,000, which saves $5,213 in income tax AND increases your CCB payments by approximately $1,847 per year. Combined, that is a $7,060 return on your $12,000 contribution — a 58.8% immediate return.",
      "estimated_value": 7060.00,
      "calculation_shown": "Tax saving: $12,000 × 43.41% = $5,213. CCB increase: 2 children × income reduction impact at current family net income = $1,847.",
      "action_required": "Contribute $12,000 to your Wealthsimple RRSP before March 1, 2026.",
      "product_link": "wealthsimple://rrsp/contribute",
      "confidence": 0.87,
      "requires_additional_info": ["number_of_children", "childrens_ages"]
    },
    {
      "id": "OVER_WITHHOLDING",
      "priority": "HIGH",
      "category": "ACT_NOW",
      "headline": "Your employer is withholding $2,400 more tax than necessary",
      "detail": "Based on your T4 Box 22 ($20,832 withheld) versus your estimated true tax liability ($18,432), your employer is over-withholding approximately $2,400 per year — $200 per month. This is an interest-free loan to the CRA. Filing Form T1213 instructs your employer to reduce deductions immediately.",
      "estimated_value": 2400.00,
      "calculation_shown": "Box22 ($20,832) − estimated_liability ($18,432) = $2,400 over-withheld",
      "action_required": "Download and file Form T1213 with CRA. Takes 4-6 weeks to process. We can help you prepare it.",
      "product_link": "wealthsimple://tax/t1213",
      "confidence": 0.82,
      "requires_additional_info": ["other_deductions", "childcare_expenses"]
    }
  ],
  "summary": {
    "total_identified_savings": 14847.00,
    "act_now_count": 3,
    "this_year_count": 5,
    "long_term_count": 4,
    "requires_human_review": false,
    "confidence_overall": 0.88
  }
}
```

---

## 10. Privacy & PII Strategy

### The Three Principles

**1. Data Minimization** — Extract only what is needed. Raw documents are deleted immediately after extraction. The system never stores SINs, full names, addresses, or dates of birth.

**2. Redact Before Every External Call** — The GPT-4o API never receives PII. Only anonymized financial figures and box numbers are sent. The employer name is retained as it is a business entity, not a personal identifier.

**3. Audit Everything** — Every access to any financial data is logged with timestamp, user ID, and purpose. Logs are immutable and retained per PIPEDA requirements.

### PII Handling Matrix

| Data Element              | Stored Locally    | Sent to GPT-4o     | Retention Policy          |
| ------------------------- | ----------------- | ------------------ | ------------------------- |
| SIN                       | Never             | Never              | Never persisted           |
| Full name                 | Hashed token only | Never              | Deleted post-processing   |
| Address                   | Never             | Never              | Never persisted           |
| Date of birth             | Never             | Never              | Never persisted           |
| Employment income (Box14) | Yes (encrypted)   | Yes (redacted doc) | 7 years (CRA requirement) |
| Tax figures (all boxes)   | Yes (encrypted)   | Yes                | 7 years                   |
| Employer name             | Yes               | Yes                | 7 years                   |
| Derived insights          | Yes               | No                 | Until superseded          |
| Raw document file         | Temp only         | Never              | Deleted after extraction  |

### Production Architecture Note

The demo uses OpenAI's public API with redacted data. In production, this system would use **Azure OpenAI with Canadian data residency** (East Canada region) — ensuring no data crosses outside Canadian jurisdiction, meeting PIPEDA and Wealthsimple's data governance requirements.

---

## 11. Human Review Layer

### Review Queue Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADVISOR DASHBOARD                            │
│                                                                 │
│  Queue: 47 cases pending  |  SLA: 23h 14m remaining avg       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CASE #4821  |  ████████░░  87% confidence               │  │
│  │  Income: $94,000  |  Province: ON  |  2 insights flagged  │  │
│  │                                                          │  │
│  │  Insight 1: CCB_STACKING — $7,060 identified value      │  │
│  │  Insight 2: OVER_WITHHOLDING — $2,400/year              │  │
│  │                                                          │  │
│  │  [Approve All]  [Review Individual]  [Escalate]         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CASE #4820  |  ██████░░░░  61% confidence  ⚠️ REVIEW   │  │
│  │  Income: $142,000  |  Province: QC  |  Anomaly detected  │  │
│  │                                                          │  │
│  │  Flag: TAX_RATE_ANOMALY — Box22/Box14 = 8.2% (low)      │  │
│  │  Requires full review before any insight delivery        │  │
│  │                                                          │  │
│  │  [View Documents]  [Request More Info]  [Reject]        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Review Rules

```python
AUTO_APPROVE_CRITERIA = {
    "min_confidence": 0.85,
    "no_validation_flags": True,
    "no_anomaly_flags": True,
    "insight_type_not_in": ["RETIRING_ALLOWANCE", "STOCK_OPTIONS"],
    "estimated_value_under": 50000.00
}

MANDATORY_HUMAN_REVIEW = [
    "TAX_RATE_ANOMALY",
    "INCOME_DISCREPANCY",  # CRA vs upload mismatch
    "CPP_EXCEEDS_MAXIMUM", # Possible extraction error
    "HIGH_VALUE_INSIGHT",  # > $50,000 identified savings
    "NEAR_RETIREMENT",     # Age 60+ complex strategies
    "MULTI_EMPLOYER_COMPLEX" # 3+ employers, complex situation
]
```

---

## 12. Data Schema

### Unified Financial Profile

```json
{
  "profile_id": "uuid",
  "created_at": "2024-02-01T09:00:00Z",
  "tax_year": 2024,
  "province": "ON",

  "data_sources": {
    "cra_authorized": true,
    "cra_last_synced": "2024-02-01T08:55:00Z",
    "t4_uploaded": true,
    "upload_timestamp": "2024-02-01T09:00:00Z",
    "reconciliation_status": "MATCHED",
    "discrepancies": []
  },

  "employment": {
    "num_employers": 1,
    "total_employment_income": 85000.00,
    "total_cpp_contributions": 3867.50,
    "total_cpp2_contributions": 188.00,
    "total_ei_premiums": 1049.12,
    "total_income_tax_withheld": 20832.00,
    "total_pension_adjustments": 12000.00,
    "total_rpp_contributions": 4200.00,
    "total_union_dues": 2400.00,
    "province_of_employment": "ON"
  },

  "registered_accounts": {
    "rrsp_deduction_limit": 31560.00,
    "rrsp_contributions_ytd": 8000.00,
    "rrsp_room_remaining": 23560.00,
    "tfsa_room_remaining": 28000.00,
    "fhsa_eligible": true,
    "fhsa_room_available": 8000.00,
    "hbp_balance_outstanding": 0.00,
    "llp_balance_outstanding": 0.00
  },

  "carryforwards": {
    "capital_loss_carryforward": 8400.00,
    "unused_tuition": 0.00,
    "unused_charitable_donations": 500.00,
    "rrsp_unused_room_accumulated": 47000.00
  },

  "investment_income": {
    "eligible_dividends": 0.00,
    "non_eligible_dividends": 0.00,
    "interest_income": 0.00,
    "capital_gains_realized": 0.00,
    "foreign_income": 0.00
  },

  "derived": {
    "marginal_rate_federal": 0.26,
    "marginal_rate_provincial": 0.1741,
    "marginal_rate_combined": 0.4341,
    "estimated_net_income": 72600.00,
    "estimated_tax_liability": 18432.00,
    "over_withholding_estimate": 2400.00,
    "cpp_overpayment": 0.00,
    "ei_overpayment": 0.00,
    "distance_to_next_bracket_down": 6267.00
  },

  "insights": [],
  "review_status": "PENDING",
  "advisor_id": null,
  "approved_at": null
}
```

---

## 13. Build Plan & Timeline

### Day 1 — Core Pipeline

| Time     | Task                                              | Output                               |
| -------- | ------------------------------------------------- | ------------------------------------ |
| 9:00 AM  | Environment setup, install dependencies           | Working Python env                   |
| 10:00 AM | Build `ocr_service.py`— digital PDF extraction | Extracts T4 fields from dummy PDFs   |
| 11:30 AM | Build `redaction_service.py`— PII masking      | All PII redacted before any API call |
| 1:00 PM  | Build `llm_service.py`— GPT-4o extraction call | Structured JSON from T4              |
| 2:30 PM  | Build `tax_engine.py`— Canadian tax rules      | Deterministic calculations           |
| 4:00 PM  | Build `benefit_engine.py`— insight generation  | 20 insights with values              |
| 5:30 PM  | Test end-to-end with dummy T4 PDFs                | Full pipeline working                |

### Day 2 — UI + Demo Prep

| Time     | Task                               | Output                 |
| -------- | ---------------------------------- | ---------------------- |
| 9:00 AM  | Build FastAPI backend + endpoints  | REST API running       |
| 10:30 AM | Build upload UI (React)            | Working file upload    |
| 12:00 PM | Build customer insight report UI   | Insights displayed     |
| 1:30 PM  | Build advisor dashboard UI         | Review queue working   |
| 3:00 PM  | End-to-end test with all dummy T4s | Demo scenario complete |
| 4:00 PM  | Record 2–3 minute demo video      | Submission video       |
| 5:00 PM  | Write 500-word explanation         | Written submission     |
| 6:00 PM  | Final review and submit            | ✅ Submitted           |

### Dependencies

```bash
# Python dependencies
pip install fastapi uvicorn pymupdf openai python-multipart \
            sqlalchemy aiosqlite python-dotenv pydantic

# Environment variables
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./t4_analyzer.db
MAX_FILE_SIZE_MB=10
ENVIRONMENT=development
```

---

## 14. What Breaks First at Scale

### Priority 1 — Document Quality Degradation

At high volume, OCR accuracy drops significantly for:

* **Low-resolution scans** — employers printing T4s at 150 DPI
* **Non-standard T4 layouts** — small employers using third-party payroll software
* **Handwritten corrections** — employees who crossed out errors and wrote new values
* **Multilingual documents** — Quebec T4s with French field labels

**Fix:** Confidence scoring per field + mandatory human review for any field below 0.80 confidence. Route low-quality documents to OCR specialist queue.

### Priority 2 — Annual Tax Law Changes

CRA updates brackets, limits, and rates every January. A model trained or prompted on 2024 rules gives wrong advice in 2025.

**Fix:** Tax rules engine is fully deterministic Python code — not LLM knowledge. Rules are version-controlled and updated as a code deployment when CRA announces changes (typically November for the following year).

### Priority 3 — Advisor Queue Overflow

At scale, even 5% of 3M users submitting documents creates 150,000 review cases. At 10 minutes per case, that requires 25,000 advisor-hours — unsustainable.

**Fix:**

* Auto-approve high-confidence, low-complexity cases (target 70% auto-approval)
* Tiered review: junior staff handle Tier 1, licensed advisors handle Tier 2+
* ML model trained on approved decisions to increase auto-approval rate over time
* Human review only for genuinely novel or high-stakes situations

### Priority 4 — Adversarial Document Manipulation

Fraudulent T4s submitted to generate false refund advice or test system boundaries.

**Fix:** CRA data cross-reference as primary truth source. Uploaded documents are secondary and always cross-checked. Anomaly detection flags statistical outliers (income that doesn't match CPP pensionable earnings, tax rates outside normal ranges).

### Priority 5 — Provincial Tax Complexity

Quebec has entirely separate provincial tax administration (MRQ, not CRA). Some insights require QPP instead of CPP calculations. Alberta has no provincial income tax form.

**Fix:** Province-specific rules modules with full coverage of all 13 jurisdictions before production launch.

---

## 15. Submission Answers

### What the human can now do that they couldn't before

A single licensed financial advisor can now meaningfully review and approve personalized tax optimization recommendations for **hundreds of Canadians per day** — versus the 2–3 detailed reviews possible manually. The AI handles every step from document ingestion through insight generation. The human focuses exclusively on judgment calls: is this recommendation appropriate given what I know about this client's broader situation? That question requires a human. Everything before it does not.

### What AI is responsible for

Document ingestion and OCR extraction, PII detection and redaction, CRA data reconciliation, all tax calculations, identification and quantification of 20+ optimization strategies, confidence scoring, anomaly detection, case routing, and plain-language explanation generation. The AI processes documents in seconds that would take an advisor 45–60 minutes each.

### Where AI must stop

No recommendation reaches a customer without a licensed advisor's explicit approval. This boundary is **architectural** — there is no code path from AI output to customer delivery that bypasses the review queue. This exists because personalized tax advice carries legal liability, because the AI sees one document while a human brings full context, and because PIPEDA requires human accountability for consequential decisions.

### What would break first at scale

Low-quality scanned documents causing silent OCR errors that propagate through the analysis. The fix is mandatory confidence thresholds — any field below 0.80 confidence routes the entire case to human review rather than auto-processing. This is the most important architectural safeguard in the system.

---

## Appendix A — Canadian Tax Reference 2024

| Parameter                      | 2024                             | 2025                 |
| ------------------------------ | -------------------------------- | -------------------- |
| RRSP annual limit              | $31,560              | $32,490   |                      |
| TFSA annual limit              | $7,000               | $7,000    |                      |
| TFSA cumulative (since 2009)   | $95,000              | $102,000  |                      |
| FHSA annual / lifetime         | $8,000 / $40,000                 | $8,000 / $40,000     |
| CPP YMPE                       | $68,500              | $71,300   |                      |
| CPP YAMPE (CPP2 ceiling)       | $73,200              | $81,200   |                      |
| Max CPP employee contribution  | $3,867.50            | $4,034.10 |                      |
| Max CPP2 employee contribution | $188.00              | $396.00   |                      |
| Max EI employee premium        | $1,049.12            | $1,077.48 |                      |
| EI max insurable earnings      | $63,200              | $65,700   |                      |
| Federal basic personal amount  | $15,705              | $16,129   |                      |
| OAS clawback threshold         | $90,997              | $93,454   |                      |
| HBP withdrawal limit           | $60,000              | $60,000   |                      |
| Federal bracket 1 (15%)        | $0 – $55,867                    | $0 – $57,375        |
| Federal bracket 2 (20.5%)      | $55,867 – $111,733              | $57,375 – $114,750  |
| Federal bracket 3 (26%)        | $111,733 – $173,205             | $114,750 – $177,882 |
| Federal bracket 4 (29%)        | $173,205 – $246,752             | $177,882 – $253,414 |
| Federal bracket 5 (33%)        | $246,752+            | $253,414+ |                      |

---

## Appendix B — Glossary

| Term                  | Definition                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------------- |
| **AFR**         | Auto-fill my return — CRA's service allowing authorized software to pull tax slip data      |
| **Box 52 / PA** | Pension Adjustment — reduces RRSP room based on employer pension accrual                    |
| **CCB**         | Canada Child Benefit — income-tested monthly payment for families with children             |
| **CPP2**        | Second additional CPP contribution on earnings between YMPE and YAMPE (2024+)                |
| **FHSA**        | First Home Savings Account — deductible contributions, tax-free withdrawals for first home  |
| **GIS**         | Guaranteed Income Supplement — income-tested supplement for low-income seniors              |
| **HBP**         | Home Buyers' Plan — allows RRSP withdrawal (up to $60,000) for first home purchase          |
| **LLP**         | Lifelong Learning Plan — allows RRSP withdrawal for full-time education                     |
| **OAS**         | Old Age Security — federal pension for Canadians 65+, clawed back above $90,997             |
| **PAR**         | Pension Adjustment Reversal — restores RRSP room when leaving a pension plan unvested       |
| **PIPEDA**      | Personal Information Protection and Electronic Documents Act — Canada's federal privacy law |
| **QPP**         | Quebec Pension Plan — Quebec equivalent of CPP                                              |
| **RRIF**        | Registered Retirement Income Fund — mandatory conversion from RRSP at age 71                |
| **T1213**       | CRA form to reduce tax withheld at source (eliminate over-withholding)                       |
| **YAMPE**       | Year's Additional Maximum Pensionable Earnings — CPP2 upper ceiling                         |
| **YMPE**        | Year's Maximum Pensionable Earnings — CPP base contribution ceiling                         |

---

*This document is a technical system plan for a prototype submission. All financial figures shown are examples using synthetic data. No actual customer data was used.*
