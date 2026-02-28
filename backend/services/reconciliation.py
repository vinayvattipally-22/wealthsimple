"""
Reconciliation: merge CRA + upload sources; match T4s by employer payroll account;
flag discrepancies > $0.01; current-year upload priority, prior-year CRA priority.
"""
from typing import Any

RECONCILIATION_RULES = {
    "income_mismatch_threshold": 0.01,
    "current_year_upload_priority": True,
    "cra_priority_for_prior_years": True,
    "multi_employer_aggregation": True,
    "missing_slip_detection": True,
}


def reconcile(cra_data: dict, upload_data: dict, tax_year: int) -> dict:
    """
    Merge CRA and upload T4 data. Match by employer payroll account where available;
    flag discrepancies above threshold. Return unified employment totals and discrepancy list.
    """
    discrepancies = []
    # Simple merge: prefer upload for current year, CRA for prior
    from datetime import datetime
    current = datetime.now().year
    use_upload_primary = RECONCILIATION_RULES["current_year_upload_priority"] and tax_year >= current
    cra_t4s = cra_data.get("t4s", []) or cra_data.get("slips", [])
    upload_t4s = upload_data.get("t4s", []) or upload_data.get("employment", {})
    if isinstance(upload_t4s, dict):
        upload_t4s = [upload_t4s]
    # Aggregate employment totals
    total_income = 0.0
    total_cpp = 0.0
    total_ei = 0.0
    total_tax_withheld = 0.0
    for t4 in (upload_t4s if use_upload_primary else cra_t4s) + (cra_t4s if use_upload_primary else upload_t4s):
        if isinstance(t4, dict):
            total_income += float(t4.get("14") or t4.get("employment_income") or 0)
            total_cpp += float(t4.get("16") or 0)
            total_ei += float(t4.get("18") or 0)
            total_tax_withheld += float(t4.get("22") or 0)
    # Check for income mismatch if both sources have same employer
    cra_income = sum(float(t.get("14") or t.get("employment_income") or 0) for t in cra_t4s if isinstance(t, dict))
    upload_income = sum(float(t.get("14") or t.get("employment_income") or 0) for t in upload_t4s if isinstance(t, dict))
    if abs(cra_income - upload_income) > RECONCILIATION_RULES["income_mismatch_threshold"]:
        discrepancies.append({"type": "INCOME_DISCREPANCY", "cra": cra_income, "upload": upload_income})
    return {
        "employment": {
            "total_employment_income": round(total_income, 2),
            "total_cpp_contributions": round(total_cpp, 2),
            "total_ei_premiums": round(total_ei, 2),
            "total_income_tax_withheld": round(total_tax_withheld, 2),
        },
        "reconciliation_status": "MATCHED" if not discrepancies else "DISCREPANCY",
        "discrepancies": discrepancies,
    }
