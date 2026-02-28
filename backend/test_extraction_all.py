"""Test OCR extraction on all PDFs: original, copy, and all 10 generated T4s."""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from services.ocr_service import _parse_fields_spatial

# Expected values for generated PDFs (from generate_test_t4s.py)
EXPECTED = {
    "customer_1": {
        2020: {"14": 42500, "16": 2047.50, "18": 671.50, "22": 4854.33},
        2021: {"14": 44200, "16": 2218.15, "18": 698.36, "22": 5310.43},
        2022: {"14": 46800, "16": 2468.10, "18": 739.44, "22": 5900.56},
        2023: {"14": 50100, "16": 2772.70, "18": 816.63, "22": 6700.17},
        2024: {"14": 55000, "16": 3064.25, "18": 913.00, "22": 7420.84},
    },
    "customer_2": {
        2020: {"14": 72000, "16": 2898.00, "18": 856.36, "22": 12536.04},
        2021: {"14": 76500, "16": 3166.45, "18": 889.54, "22": 13824.38},
        2022: {"14": 82000, "16": 3499.80, "18": 952.74, "22": 15467.67},
        2023: {"14": 88500, "16": 3754.45, "18": 1002.45, "22": 17287.26},
        2024: {"14": 95000, "16": 3867.50, "18": 1049.12, "22": 19044.81},
    },
}


def fmt(v):
    return f"${v:,.2f}" if isinstance(v, float) else str(v)


def test_pdf(label, path, expected=None):
    fields = _parse_fields_spatial(path)
    boxes = {k: v for k, v in fields.items() if isinstance(k, str) and k.isdigit()}
    year = fields.get("tax_year")
    prov = fields.get("province_code")

    status = "OK"
    mismatches = []
    if expected:
        for box, exp_val in expected.items():
            actual = boxes.get(box)
            if actual is None:
                mismatches.append(f"Box {box}: MISSING (expected {fmt(exp_val)})")
                status = "FAIL"
            elif abs(actual - exp_val) > 0.02:
                mismatches.append(f"Box {box}: {fmt(actual)} != {fmt(exp_val)}")
                status = "FAIL"

    print(f"  [{status}] {label}")
    print(f"       Year={year}  Prov={prov}  Boxes: {', '.join(f'{k}={fmt(v)}' for k, v in sorted(boxes.items(), key=lambda x: int(x[0])))}")
    if mismatches:
        for m in mismatches:
            print(f"       !! {m}")
    return status == "OK"


print("=" * 70)
print("  OCR EXTRACTION TEST — ALL PDFs")
print("=" * 70)

results = []

# Original template
print("\n--- Original Template ---")
results.append(test_pdf(
    "T4_edited.pdf (original)",
    "../T4_edited.pdf",
    {"14": 39991.25, "16": 2171.26, "18": 663.83, "22": 1746.33},
))

# Exact copy
print("\n--- Exact Copy ---")
results.append(test_pdf(
    "T4_original_copy.pdf (duplicate)",
    "../T4_original_copy.pdf",
    {"14": 39991.25, "16": 2171.26, "18": 663.83, "22": 1746.33},
))

# Generated PDFs — Customer 1
print("\n--- Customer 1 (Sarah Thompson) ---")
for year in range(2020, 2025):
    results.append(test_pdf(
        f"T4_{year}_Thompson.pdf",
        f"../test_data/customer_1/T4_{year}_Thompson.pdf",
        EXPECTED["customer_1"][year],
    ))

# Generated PDFs — Customer 2
print("\n--- Customer 2 (James Richardson) ---")
for year in range(2020, 2025):
    results.append(test_pdf(
        f"T4_{year}_Richardson.pdf",
        f"../test_data/customer_2/T4_{year}_Richardson.pdf",
        EXPECTED["customer_2"][year],
    ))

print("\n" + "=" * 70)
passed = sum(results)
total = len(results)
print(f"  RESULTS: {passed}/{total} passed")
if passed == total:
    print("  All PDFs extract correctly!")
else:
    print(f"  {total - passed} PDF(s) had extraction issues")
print("=" * 70)
