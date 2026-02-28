"""
Benefit phase-out rates — CCB, GST credit, OAS clawback, GIS (Appendix A).
"""
# OAS clawback threshold (net income)
OAS_CLAWBACK_THRESHOLD = {2024: 90_997, 2025: 93_454}

# CCB phase-out: approximate 7% per child under 6, 3.2% per child 6–17 (income over threshold)
# Simplified: we only expose threshold for "near clawback" insights.
CCB_PHASE_OUT_START = 32_797  # approximate; varies by family size

# GST/HST credit — income-tested; phase-out ranges
GST_CREDIT_PHASE_OUT = 39_826  # single; different for couples

# GIS — Guaranteed Income Supplement; low-income seniors
# Used for "near retirement" insight logic; no exact rate here.


def get_oas_clawback_threshold(tax_year: int) -> float:
    return OAS_CLAWBACK_THRESHOLD.get(tax_year, 90_997)
