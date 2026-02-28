#!/usr/bin/env python3
"""
generate_test_t4s.py — Generate 10 test T4 PDFs from T4_edited.pdf template.

Creates test_data/customer_1/ and test_data/customer_2/ directories, each with
5 T4 PDFs for tax years 2020-2024 with CRA-consistent box values.

Usage:
    cd d:/Wealthsimple
    backend/.venv/Scripts/python.exe generate_test_t4s.py
"""
import os
import sys

import fitz  # PyMuPDF

# ---------------------------------------------------------------------------
# CRA Rate Tables (2020-2024)
# ---------------------------------------------------------------------------

CPP_RATES = {
    2020: {"ympe": 58_700, "exemption": 3_500, "rate": 0.0525, "max_contrib": 2_898.00},
    2021: {"ympe": 61_600, "exemption": 3_500, "rate": 0.0545, "max_contrib": 3_166.45},
    2022: {"ympe": 64_900, "exemption": 3_500, "rate": 0.0570, "max_contrib": 3_499.80},
    2023: {"ympe": 66_600, "exemption": 3_500, "rate": 0.0595, "max_contrib": 3_754.45},
    2024: {"ympe": 68_500, "exemption": 3_500, "rate": 0.0595, "max_contrib": 3_867.50},
}

EI_RATES = {
    2020: {"max_insurable": 54_200, "rate": 0.0158, "max_premium": 856.36},
    2021: {"max_insurable": 56_300, "rate": 0.0158, "max_premium": 889.54},
    2022: {"max_insurable": 60_300, "rate": 0.0158, "max_premium": 952.74},
    2023: {"max_insurable": 61_500, "rate": 0.0163, "max_premium": 1_002.45},
    2024: {"max_insurable": 63_200, "rate": 0.0166, "max_premium": 1_049.12},
}

FEDERAL_BRACKETS = {
    2020: [(0.15, 0, 48_535), (0.205, 48_535, 97_069), (0.26, 97_069, 150_473),
           (0.29, 150_473, 214_368), (0.33, 214_368, None)],
    2021: [(0.15, 0, 49_020), (0.205, 49_020, 98_040), (0.26, 98_040, 151_978),
           (0.29, 151_978, 216_511), (0.33, 216_511, None)],
    2022: [(0.15, 0, 50_197), (0.205, 50_197, 100_392), (0.26, 100_392, 155_625),
           (0.29, 155_625, 221_708), (0.33, 221_708, None)],
    2023: [(0.15, 0, 53_359), (0.205, 53_359, 106_717), (0.26, 106_717, 165_430),
           (0.29, 165_430, 235_675), (0.33, 235_675, None)],
    2024: [(0.15, 0, 55_867), (0.205, 55_867, 111_733), (0.26, 111_733, 173_205),
           (0.29, 173_205, 246_752), (0.33, 246_752, None)],
}

FEDERAL_BPA = {2020: 13_229, 2021: 13_808, 2022: 14_398, 2023: 15_000, 2024: 15_705}

ONTARIO_BRACKETS = {
    2020: [(0.0505, 0, 44_740), (0.0915, 44_740, 89_482), (0.1116, 89_482, 150_000),
           (0.1216, 150_000, 220_000), (0.1316, 220_000, None)],
    2021: [(0.0505, 0, 45_142), (0.0915, 45_142, 90_287), (0.1116, 90_287, 150_000),
           (0.1216, 150_000, 220_000), (0.1316, 220_000, None)],
    2022: [(0.0505, 0, 46_226), (0.0915, 46_226, 92_454), (0.1116, 92_454, 150_000),
           (0.1216, 150_000, 220_000), (0.1316, 220_000, None)],
    2023: [(0.0505, 0, 49_231), (0.0915, 49_231, 98_463), (0.1116, 98_463, 150_000),
           (0.1216, 150_000, 220_000), (0.1316, 220_000, None)],
    2024: [(0.0505, 0, 51_446), (0.0915, 51_446, 102_894), (0.1116, 102_894, 150_000),
           (0.1216, 150_000, 220_000), (0.1316, 220_000, None)],
}

ONTARIO_BPA = {2020: 10_783, 2021: 10_880, 2022: 11_141, 2023: 11_865, 2024: 11_865}


# ---------------------------------------------------------------------------
# Tax Calculation Functions
# ---------------------------------------------------------------------------

def _tax_from_brackets(income: float, brackets: list) -> float:
    tax = 0.0
    for rate, low, high in brackets:
        if income <= low:
            break
        taxable = min(income, high) - low if high else income - low
        tax += taxable * rate
    return tax


def calculate_cpp(income: float, year: int) -> float:
    r = CPP_RATES[year]
    pensionable = min(income, r["ympe"])
    contribution = (pensionable - r["exemption"]) * r["rate"]
    return round(min(max(contribution, 0), r["max_contrib"]), 2)


def calculate_ei(income: float, year: int) -> float:
    r = EI_RATES[year]
    insurable = min(income, r["max_insurable"])
    premium = insurable * r["rate"]
    return round(min(premium, r["max_premium"]), 2)


def calculate_tax(income: float, year: int) -> float:
    cpp = calculate_cpp(income, year)
    ei = calculate_ei(income, year)

    # Federal tax
    fed_tax = _tax_from_brackets(income, FEDERAL_BRACKETS[year])
    fed_credit = FEDERAL_BPA[year] * 0.15 + cpp * 0.15 + ei * 0.15
    fed_net = max(0, fed_tax - fed_credit)

    # Ontario provincial tax
    prov_tax = _tax_from_brackets(income, ONTARIO_BRACKETS[year])
    prov_credit = ONTARIO_BPA[year] * 0.0505 + cpp * 0.0505 + ei * 0.0505
    prov_net = max(0, prov_tax - prov_credit)

    return round(fed_net + prov_net, 2)


# ---------------------------------------------------------------------------
# Customer Data
# ---------------------------------------------------------------------------

CUSTOMERS = [
    {
        "id": 1,
        "folder": "customer_1",
        "employer_name": "Maple Leaf Tech Solutions Inc",
        "first_name": "Sarah",
        "last_name": "Thompson",
        "sin": "123456789",
        "address_line1": "45 Birchwood Drive, Unit 302",
        "address_line2": "Toronto, ON",
        "postal_code": "M5V2T6",
        "incomes": {
            2020: 42_500.00,
            2021: 44_200.00,
            2022: 46_800.00,
            2023: 50_100.00,
            2024: 55_000.00,
        },
    },
    {
        "id": 2,
        "folder": "customer_2",
        "employer_name": "Northern Shield Financial Corp",
        "first_name": "James",
        "last_name": "Richardson",
        "sin": "987654321",
        "address_line1": "789 Lakeshore Blvd, Suite 1501",
        "address_line2": "Mississauga, ON",
        "postal_code": "L5H1H4",
        "incomes": {
            2020: 72_000.00,
            2021: 76_500.00,
            2022: 82_000.00,
            2023: 88_500.00,
            2024: 95_000.00,
        },
    },
]

# Template original values (what to search for in T4_edited.pdf)
TEMPLATE = {
    "employer_name": "Nandos Canada Corporate Inc",
    "year": "2024",
    "sin": "56764456",
    "last_name": "Vattipally",
    "first_name": "Vinay",
    "address_line1": "123 Some place, Unit 2111",
    "address_line2": "Scarborough, ON",
    "postal_code": "M1W3G4",
    "box14_int": "39991", "box14_dec": ".25",
    "box22_int": "1746",  "box22_dec": ".33",
    "box16_int": "2171",  "box16_dec": ".26",
    "box18_int": "663",   "box18_dec": ".83",
}


# ---------------------------------------------------------------------------
# PDF Modification Helpers
# ---------------------------------------------------------------------------
# Two-pass approach:
#   Pass 1: Collect all (rect, new_text, fontsize, fontname) pairs and add redact annotations
#   Pass 2: apply_redactions() to permanently destroy old text
#   Pass 3: Insert all new text at saved positions
#
# This ensures the old text layer is removed and OCR reads the new values.

def _collect_text_replacement(page, old: str, new: str, fontsize: float = 8.8,
                              fontname: str = "helv", y_max: float = None,
                              replacements: list = None):
    """Find old text, schedule it for redaction, and queue the new text for insertion."""
    rects = page.search_for(old)
    if y_max is not None:
        rects = [r for r in rects if r.y0 < y_max]
    for rect in rects:
        page.add_redact_annot(rect, fill=(1, 1, 1))
        replacements.append((fitz.Point(rect.x0, rect.y1 - 1), new, fontname, fontsize))


def _collect_split_replacement(page, old_int: str, old_dec: str,
                               new_values, fontsize: float = 8.8,
                               replacements: list = None):
    """Find split monetary values, schedule redaction, queue new values for insertion."""
    if isinstance(new_values, (int, float)):
        values_list = None
        single = float(new_values)
    else:
        values_list = [float(v) for v in new_values]
        single = None

    rects_int = page.search_for(old_int)
    rects_int.sort(key=lambda r: (round(r.y0), r.x0))

    rects_dec = page.search_for(old_dec)
    rects_dec.sort(key=lambda r: (round(r.y0), r.x0))

    for i, rect in enumerate(rects_int):
        val = single if values_list is None else values_list[i]
        int_str = str(int(val))
        page.add_redact_annot(rect, fill=(1, 1, 1))
        replacements.append((fitz.Point(rect.x0, rect.y1 - 1), int_str, "helv", fontsize))

    for i, rect in enumerate(rects_dec):
        val = single if values_list is None else values_list[i]
        cents = int(round((val % 1) * 100))
        dec_str = f".{cents:02d}"
        page.add_redact_annot(rect, fill=(1, 1, 1))
        replacements.append((fitz.Point(rect.x0, rect.y1 - 1), dec_str, "helv", fontsize))


# ---------------------------------------------------------------------------
# T4 Generation
# ---------------------------------------------------------------------------

def generate_t4(template_path: str, output_path: str, customer: dict, year: int):
    """Generate a single T4 PDF by modifying the template with calculated values."""
    income = customer["incomes"][year]
    cpp = calculate_cpp(income, year)
    ei = calculate_ei(income, year)
    tax = calculate_tax(income, year)
    ei_insurable = min(income, EI_RATES[year]["max_insurable"])
    cpp_pensionable = min(income, CPP_RATES[year]["ympe"])

    doc = fitz.open(template_path)
    page = doc[0]

    # Pass 1: Collect all replacements and add redaction annotations
    replacements: list[tuple] = []  # (point, text, fontname, fontsize)

    # Simple text fields
    _collect_text_replacement(page, TEMPLATE["employer_name"], customer["employer_name"],
                              fontsize=8.1, replacements=replacements)
    _collect_text_replacement(page, TEMPLATE["last_name"], customer["last_name"],
                              fontsize=6.8, replacements=replacements)
    _collect_text_replacement(page, TEMPLATE["first_name"], customer["first_name"],
                              fontsize=6.8, replacements=replacements)
    _collect_text_replacement(page, TEMPLATE["sin"], customer["sin"],
                              fontsize=8.0, replacements=replacements)
    _collect_text_replacement(page, TEMPLATE["address_line1"], customer["address_line1"],
                              fontsize=7.5, replacements=replacements)
    _collect_text_replacement(page, TEMPLATE["address_line2"], customer["address_line2"],
                              fontsize=7.5, replacements=replacements)
    _collect_text_replacement(page, TEMPLATE["postal_code"], customer["postal_code"],
                              fontsize=7.5, replacements=replacements)

    # Year (positional filter: only the Year box near top of page)
    _collect_text_replacement(page, TEMPLATE["year"], str(year),
                              fontsize=8.8, y_max=100, replacements=replacements)

    # Box 14 / 24 / 26 (triple occurrence: income, EI insurable, CPP pensionable)
    _collect_split_replacement(
        page, TEMPLATE["box14_int"], TEMPLATE["box14_dec"],
        [income, ei_insurable, cpp_pensionable], replacements=replacements,
    )

    # Box 22 (income tax deducted)
    _collect_split_replacement(page, TEMPLATE["box22_int"], TEMPLATE["box22_dec"],
                               tax, replacements=replacements)

    # Box 16 (CPP contributions)
    _collect_split_replacement(page, TEMPLATE["box16_int"], TEMPLATE["box16_dec"],
                               cpp, replacements=replacements)

    # Box 18 (EI premiums)
    _collect_split_replacement(page, TEMPLATE["box18_int"], TEMPLATE["box18_dec"],
                               ei, replacements=replacements)

    # Pass 2: Apply all redactions — permanently destroys old text
    page.apply_redactions()

    # Pass 3: Insert all new text at saved positions
    for point, text, fontname, fontsize in replacements:
        page.insert_text(point, text, fontname=fontname, fontsize=fontsize, color=(0, 0, 0))

    # Box 45 (dental=1) and Province (ON) stay as-is

    doc.save(output_path)
    doc.close()

    return {
        "income": income, "cpp": cpp, "ei": ei, "tax": tax,
        "ei_insurable": ei_insurable, "cpp_pensionable": cpp_pensionable,
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    template_path = os.path.join(project_root, "sample_docs", "T4_edited.pdf")

    if not os.path.exists(template_path):
        print(f"ERROR: Template not found at {template_path}")
        sys.exit(1)

    print("=" * 90)
    print("Generating 10 Test T4 PDFs")
    print("=" * 90)

    for customer in CUSTOMERS:
        output_dir = os.path.join(project_root, "test_data", customer["folder"])
        os.makedirs(output_dir, exist_ok=True)

        name = f"{customer['first_name']} {customer['last_name']}"
        print(f"\nCustomer {customer['id']}: {name}")
        print(f"  Employer: {customer['employer_name']}")
        print(f"  {'Year':<6} {'Income':>12} {'CPP(16)':>10} {'EI(18)':>10} "
              f"{'Tax(22)':>10} {'EI_Ins(24)':>12} {'CPP_Pen(26)':>12}")
        print(f"  {'-'*6} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*12} {'-'*12}")

        for year in range(2020, 2025):
            filename = f"T4_{year}_{customer['last_name']}.pdf"
            output_path = os.path.join(output_dir, filename)
            vals = generate_t4(template_path, output_path, customer, year)

            print(f"  {year:<6} {vals['income']:>12,.2f} {vals['cpp']:>10,.2f} "
                  f"{vals['ei']:>10,.2f} {vals['tax']:>10,.2f} "
                  f"{vals['ei_insurable']:>12,.2f} {vals['cpp_pensionable']:>12,.2f}")

    test_dir = os.path.join(script_dir, "test_data")
    print(f"\nDone! Generated 10 T4 PDFs in {test_dir}/")

    # --- Round-trip verification with OCR ---
    print("\n" + "=" * 90)
    print("Round-trip OCR Verification")
    print("=" * 90)

    sys.path.insert(0, os.path.join(project_root, "backend"))
    from services.ocr_service import _parse_fields_spatial

    all_ok = True
    for customer in CUSTOMERS:
        output_dir = os.path.join(project_root, "test_data", customer["folder"])
        for year in range(2020, 2025):
            filename = f"T4_{year}_{customer['last_name']}.pdf"
            pdf_path = os.path.join(output_dir, filename)
            fields = _parse_fields_spatial(pdf_path)

            income = customer["incomes"][year]
            cpp = calculate_cpp(income, year)
            ei = calculate_ei(income, year)
            tax = calculate_tax(income, year)

            # Check key boxes
            errors = []
            box14 = fields.get("14")
            if box14 is not None and abs(box14 - income) > 1:
                errors.append(f"Box14: got {box14}, expected {income}")
            box16 = fields.get("16")
            if box16 is not None and abs(box16 - cpp) > 1:
                errors.append(f"Box16: got {box16}, expected {cpp}")
            box18 = fields.get("18")
            if box18 is not None and abs(box18 - ei) > 1:
                errors.append(f"Box18: got {box18}, expected {ei}")

            extracted_year = fields.get("tax_year")
            if extracted_year and extracted_year != year:
                errors.append(f"Year: got {extracted_year}, expected {year}")

            status = "OK" if not errors else "FAIL"
            if errors:
                all_ok = False
            print(f"  {filename:<30} [{status}] {'; '.join(errors) if errors else ''}")

    print(f"\n{'All PDFs verified successfully!' if all_ok else 'Some PDFs had OCR mismatches — check above.'}")


if __name__ == "__main__":
    main()
