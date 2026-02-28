# Wealthsimple AI Tax Analyzer — How It Works

A smart tax document analyzer that reads your T4, finds every tax-saving opportunity, and tells you exactly what to do — personalized to your province, income, and history.

---

## The User Journey

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │   1. SIGN UP              2. UPLOAD              3. GET INSIGHTS    │
  │                                                                     │
  │   Create account    →    Drop your T4     →    See savings &       │
  │   with province          PDF or photo           action items        │
  │                                                                     │
  │        👤                     📄                     💡              │
  │   Name, email,          We read every         Personalized to       │
  │   password,             box on your T4        YOUR province,        │
  │   province              automatically         YOUR income           │
  │                                                                     │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Process

### Step 1 — Create Your Account

```
  ┌───────────────────────────────────────────┐
  │                                           │
  │   New User                                │
  │   ────────                                │
  │   • Enter name, email, password           │
  │   • Select your province (Ontario, BC,    │
  │     Alberta, Quebec, etc.)                │
  │   • Account is created instantly          │
  │                                           │
  │   Returning User                          │
  │   ──────────────                          │
  │   • Sign in with email + password         │
  │   • All your past documents & insights    │
  │     are waiting for you                   │
  │                                           │
  │   Two Roles                               │
  │   ─────────                               │
  │   • User — upload documents, get insights │
  │   • Advisor — review & approve insights   │
  │     before they reach the user            │
  │                                           │
  └───────────────────────────────────────────┘
```

### Step 2 — Upload Your Tax Document

```
  ┌───────────────────────────────────────────┐
  │                                           │
  │   Supported Documents                     │
  │   ────────────────────                    │
  │   • T4 (Employment Income)    PDF         │
  │   • T5 (Investment Income)    or          │
  │   • RRSP Statements           Photo       │
  │                                           │
  │   What Happens Behind the Scenes          │
  │   ────────────────────────────            │
  │                                           │
  │   You upload ──→ We read every ──→ Data   │
  │   your file       box on the       saved  │
  │                   document         to your│
  │                   (AI-powered)     account│
  │                                           │
  │   Extracted Information                   │
  │   ─────────────────────                   │
  │   • Employment income (Box 14)            │
  │   • CPP contributions (Box 16)            │
  │   • EI premiums (Box 18)                  │
  │   • Income tax withheld (Box 22)          │
  │   • Province of employment                │
  │   • Tax year                              │
  │                                           │
  │   Your document is saved to your          │
  │   account so we can compare across        │
  │   years later.                            │
  │                                           │
  └───────────────────────────────────────────┘
```

### Step 3 — AI Analysis Pipeline (5 Stages, ~15 seconds)

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   You click "Run Analysis" and watch progress in real-time:       │
  │                                                                   │
  │   ┌─────────────────────────────────────────────────────────┐    │
  │   │                                                         │    │
  │   │  STAGE 1: Read Your Data                    ✓ Complete  │    │
  │   │  Load your T4 info + check for past years              │    │
  │   │                                                         │    │
  │   │  STAGE 2: Calculate Your Taxes              ✓ Complete  │    │
  │   │  Federal + provincial tax liability                     │    │
  │   │  Your marginal tax rate                                 │    │
  │   │                                                         │    │
  │   │  STAGE 3: AI Analysis                       ✓ Complete  │    │
  │   │  GPT-4o evaluates 20+ tax strategies                   │    │
  │   │  against YOUR specific numbers                          │    │
  │   │                                                         │    │
  │   │  STAGE 4: Knowledge Check                   ✓ Complete  │    │
  │   │  Cross-reference with CRA rules                        │    │
  │   │  and latest tax guidelines                              │    │
  │   │                                                         │    │
  │   │  STAGE 5: Build Your Insights               ✓ Complete  │    │
  │   │  Prioritize recommendations                             │    │
  │   │  Add province-specific credits                          │    │
  │   │  Calculate dollar savings                               │    │
  │   │                                                         │    │
  │   └─────────────────────────────────────────────────────────┘    │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

### Step 4 — Review Your Personalized Insights

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   Insights are organized into three urgency levels:               │
  │                                                                   │
  │   🔴 ACT NOW — Time-sensitive, do these first                    │
  │   ┌─────────────────────────────────────────────────────────┐    │
  │   │ Tax Over-Withheld: Get $2,400 Back                      │    │
  │   │ Your employer withheld more tax than you owe.            │    │
  │   │ Action: File your return to receive your refund.         │    │
  │   └─────────────────────────────────────────────────────────┘    │
  │                                                                   │
  │   🟡 THIS YEAR — Do before year-end for maximum benefit          │
  │   ┌─────────────────────────────────────────────────────────┐    │
  │   │ RRSP Contribution Could Save $3,120                      │    │
  │   │ Contributing $12,000 to RRSP reduces your tax bracket.   │    │
  │   │ Calculation: $12,000 × 26% marginal rate = $3,120       │    │
  │   │ Action: Contribute before March 1 deadline.              │    │
  │   └─────────────────────────────────────────────────────────┘    │
  │                                                                   │
  │   🟢 LONG TERM — Plan for the future                             │
  │   ┌─────────────────────────────────────────────────────────┐    │
  │   │ Build Emergency Fund in TFSA                             │    │
  │   │ 3-6 months of expenses, tax-free withdrawals.            │    │
  │   │ Action: Set up automatic transfers to TFSA.              │    │
  │   └─────────────────────────────────────────────────────────┘    │
  │                                                                   │
  │   Every insight includes:                                         │
  │   • Dollar amount you could save                                  │
  │   • The math behind the number                                    │
  │   • Exactly what to do next                                       │
  │   • Direct link to the right Wealthsimple product                │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

### Step 5 — Province-Specific Benefits

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   Based on where you live, we surface credits you may not         │
  │   know about:                                                     │
  │                                                                   │
  │   Ontario                                                         │
  │   ───────                                                         │
  │   • Ontario Trillium Benefit (OTB) — up to $1,400/year           │
  │   • LIFT Credit — up to $875 for lower-income workers            │
  │   • Ontario Health Premium awareness                              │
  │                                                                   │
  │   British Columbia                                                │
  │   ────────────────                                                │
  │   • BC Climate Action Tax Credit — up to $504/year               │
  │                                                                   │
  │   Alberta                                                         │
  │   ───────                                                         │
  │   • Flat 10% tax rate = more room to invest                      │
  │                                                                   │
  │   Quebec                                                          │
  │   ──────                                                          │
  │   • Solidarity Tax Credit — up to $1,000+/year                   │
  │   • QPP differences from CPP                                      │
  │                                                                   │
  │   All Provinces                                                   │
  │   ─────────────                                                   │
  │   • GST/HST Credit — up to $496/year                             │
  │   • Canada Workers Benefit — up to $1,518                        │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

### Step 6 — Come Back Next Year (Multi-Year Comparison)

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   Year 1: Upload your 2023 T4                                    │
  │           → Get personalized insights                             │
  │           → Data saved to your account                            │
  │                                                                   │
  │                    ⬇  One year later...                           │
  │                                                                   │
  │   Year 2: Upload your 2024 T4                                    │
  │           → We automatically compare both years                   │
  │           → New insights appear:                                  │
  │                                                                   │
  │   ┌─────────────────────────────────────────────────────────┐    │
  │   │                                                         │    │
  │   │  "Your income increased 30.9% — you've moved into      │    │
  │   │   a higher bracket. An RRSP contribution of $8,000      │    │
  │   │   would bring you back to last year's rate and          │    │
  │   │   save you $2,360."                                     │    │
  │   │                                                         │    │
  │   │  "Your effective tax rate changed from 13.5% to 15.8%.  │    │
  │   │   Here's how to optimize..."                            │    │
  │   │                                                         │    │
  │   └─────────────────────────────────────────────────────────┘    │
  │                                                                   │
  │   The more years you use it, the smarter it gets.                │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

---

## Even When Savings Are Zero — We Still Help

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   Traditional tools say "No savings found." We never do that.    │
  │                                                                   │
  │   RRSP room is $0?                                                │
  │   → We explain WHY (pension adjustment? maxed out?)               │
  │   → We show how to build room for next year                      │
  │                                                                   │
  │   No tax deductions apply?                                        │
  │   → We check provincial credits you may qualify for               │
  │   → We suggest GST/HST credit, Canada Workers Benefit            │
  │                                                                   │
  │   Already optimized?                                              │
  │   → We suggest long-term strategies (emergency fund, TFSA)        │
  │   → We explain how to maintain your tax efficiency                │
  │                                                                   │
  │   Minimum 3 insights, always — because everyone deserves          │
  │   actionable financial guidance.                                  │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

---

## Advisor Review Process

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   Before insights reach the user, they go through quality         │
  │   control:                                                        │
  │                                                                   │
  │                                                                   │
  │   User uploads ──→ AI generates ──→ Advisor ──→ User sees        │
  │   document          insights         reviews     approved         │
  │                                      queue       insights         │
  │                                                                   │
  │                                                                   │
  │   What Advisors Can Do                                            │
  │   ────────────────────                                            │
  │   • Approve — insights look correct, send to user                │
  │   • Reject — something is wrong, don't show to user              │
  │   • Modify — edit values or wording before approving             │
  │   • Escalate — complex case, needs senior review                 │
  │                                                                   │
  │   Cases are prioritized by:                                       │
  │   • Confidence score (lower confidence = review first)            │
  │   • Flags (income discrepancy, tax rate anomaly, etc.)           │
  │   • 24-hour SLA deadline                                          │
  │                                                                   │
  │   Regular users CANNOT access the advisor dashboard.              │
  │   Only users with the Advisor role see the review queue.          │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

---

## Dashboard & Reports

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │   After analysis, users get a visual dashboard:                   │
  │                                                                   │
  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
  │   │   Income     │  │  Tax Owed    │  │  Total       │          │
  │   │  $72,000     │  │  $14,280     │  │  Savings     │          │
  │   │              │  │              │  │  $5,945      │          │
  │   └──────────────┘  └──────────────┘  └──────────────┘          │
  │                                                                   │
  │   ┌──────────────┐  ┌──────────────────────────────┐             │
  │   │  Marginal    │  │  Savings by Category          │             │
  │   │  Rate: 29.6% │  │                               │             │
  │   │              │  │  Act Now    ████████  $2,400   │             │
  │   │  Confidence  │  │  This Year ██████    $3,120   │             │
  │   │  Score: 0.91 │  │  Long Term ██         $425    │             │
  │   └──────────────┘  └──────────────────────────────┘             │
  │                                                                   │
  │   • Trends page — compare income & taxes across years            │
  │   • PDF reports — download a professional summary                │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

---

## Complete User Flow (Summary)

```
                          ┌──────────┐
                          │  Sign Up │
                          │  or      │
                          │  Log In  │
                          └────┬─────┘
                               │
                               ▼
                          ┌──────────┐
                          │  Upload  │
                          │  T4/T5   │
                          │  PDF     │
                          └────┬─────┘
                               │
                     AI reads every box
                     on your document
                               │
                               ▼
                          ┌──────────┐
                          │  Run     │
                          │ Analysis │
                          └────┬─────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
          ┌──────────┐  ┌──────────┐  ┌──────────┐
          │ Tax      │  │ AI       │  │ CRA      │
          │ Engine   │  │ (GPT-4o) │  │ Knowledge│
          │          │  │ Evaluates│  │ Base     │
          │ Federal  │  │ 20+ tax  │  │          │
          │ +        │  │ savings  │  │ Rules &  │
          │Provincial│  │strategies│  │ guidance │
          └────┬─────┘  └────┬─────┘  └────┬─────┘
               │              │              │
               └──────────────┼──────────────┘
                              │
                              ▼
                        ┌───────────┐
                        │  Benefit  │
                        │  Engine   │
                        │           │
                        │ Prioritize│
                        │ + Add     │
                        │ provincial│
                        │ credits   │
                        └─────┬─────┘
                              │
                 Has prior year data?
                    │              │
                   YES             NO
                    │              │
                    ▼              │
              ┌───────────┐       │
              │ Compare   │       │
              │ year over │       │
              │ year      │       │
              └─────┬─────┘       │
                    │              │
                    └──────┬───────┘
                           │
                           ▼
                     ┌───────────┐
                     │ Advisor   │
                     │ Reviews   │
                     │ (Quality  │
                     │  Control) │
                     └─────┬─────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Dashboard│ │ Insights │ │   PDF    │
        │ (Charts) │ │  (List)  │ │  Report  │
        └──────────┘ └──────────┘ └──────────┘
```

---

## What Makes This Different

| Feature | Traditional Tax Software | This App |
|---------|------------------------|----------|
| Document reading | Manual data entry | AI reads your T4 automatically |
| Tax strategies | Generic checklist | 20+ strategies evaluated against YOUR numbers |
| Zero savings | "Nothing found" | Always explains why + suggests alternatives |
| Province awareness | Same for everyone | Ontario, BC, Alberta, Quebec-specific credits |
| Multi-year | Starts fresh each year | Compares year-over-year, smarter over time |
| Quality control | None | Advisor reviews before you see insights |
| Calculations | Hidden | Every dollar amount has a visible formula |
| Action items | Vague tips | Specific next steps + direct product links |
