"""
OCR + extraction pipeline: digital PDF (PyMuPDF spatial), fallback GPT-4o Vision, field parsing, validation.
Redaction runs BEFORE any data is stored or sent externally.
"""
import base64
import os
import re
from pathlib import Path
from typing import Optional

from models.t4_schema import T4_BOX_LABELS

# Box identifiers we expect on a T4 form (used to filter out non-box numbers)
_VALID_BOX_IDS = set(T4_BOX_LABELS.keys())
# Box 10 = province of employment, box 12 = SIN — handled separately
_SKIP_BOX_IDS = {"10", "12"}
# Province abbreviations for extraction
_PROVINCE_CODES = {"ON", "BC", "AB", "QC", "MB", "SK", "NS", "NB", "NL", "PE", "NT", "NU", "YT"}


def _parse_value_from_lines(lines: list[str]) -> Optional[float]:
    """Try to combine text lines into a single float value.

    Handles patterns from PyMuPDF block extraction:
      ["39991", ".25"]  → 39991.25
      ["1"]             → 1.0
      ["2171", ".26"]   → 2171.26
    """
    combined = "".join(lines).replace(",", "").replace(" ", "")
    if not combined:
        return None
    try:
        return float(combined)
    except ValueError:
        return None


def _parse_fields_spatial(file_path: str) -> dict:
    """Parse T4 fields using PyMuPDF spatial block analysis.

    Each text block has bounding-box coordinates. Box numbers and their values
    appear together in the same block (e.g. "14\\n39991\\n.25"). This avoids
    the naive regex problem of mismatching box numbers with unrelated values.
    """
    try:
        import fitz
    except ImportError:
        return {}

    doc = fitz.open(file_path)
    if len(doc) == 0:
        doc.close()
        return {}

    page = doc[0]
    blocks = page.get_text("blocks")
    doc.close()

    fields: dict = {}
    employer_name: Optional[str] = None
    tax_year: Optional[int] = None
    province_code: Optional[str] = None
    # Track box-number-only blocks for proximity matching (second pass)
    lone_box_blocks: list[tuple] = []  # (box_id, x0, y0, x1, y1)

    for block in blocks:
        if block[6] != 0:  # skip non-text (image) blocks
            continue

        text = block[4].strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            continue

        first = lines[0]

        # --- Employer header block ---
        # Format: "Employer's name – Nom de l'employeur\nNandos Canada...\nYear\nAnnée\n2024"
        if "Employer" in first and ("name" in first.lower() or "nom" in first.lower()):
            for i, ln in enumerate(lines):
                # Year is a standalone 4-digit line
                if re.match(r"^20\d{2}$", ln):
                    tax_year = int(ln)
                # Employer name: the line right after the header, not a keyword
                elif i == 1 and not any(kw in ln.lower() for kw in ["year", "année", "employer", "nom"]):
                    employer_name = ln
            continue

        # --- Province block: "10\nON" ---
        if first == "10" and len(lines) >= 2 and lines[1].upper() in _PROVINCE_CODES:
            province_code = lines[1].upper()
            continue

        # --- Standalone year block: "2024" at top of form (y < 100) ---
        if not tax_year and re.match(r"^20\d{2}$", first) and len(lines) == 1 and block[1] < 100:
            tax_year = int(first)
            continue

        # --- Skip SIN block (box 12) ---
        if first == "12":
            continue

        # --- Standard T4 box blocks ---
        # Check if first line is a valid box identifier
        if first in _VALID_BOX_IDS or first in _SKIP_BOX_IDS:
            if first in _SKIP_BOX_IDS:
                continue

            if len(lines) >= 2:
                # Try to parse remaining lines as a numeric value
                value = _parse_value_from_lines(lines[1:])
                if value is not None:
                    fields[first] = value
                else:
                    # Box number present but value not parseable — try proximity
                    lone_box_blocks.append((first, block[0], block[1], block[2], block[3]))
            else:
                # Box number alone — need proximity matching
                lone_box_blocks.append((first, block[0], block[1], block[2], block[3]))
            continue

        # --- Handle "54\nEmployer's account number..." mixed blocks ---
        # If first line is a 2-digit number but matched something like "54\nEmployer's..."
        if re.match(r"^\d{1,2}[A-Z]?$", first) and first not in _SKIP_BOX_IDS:
            if len(lines) >= 2:
                value = _parse_value_from_lines(lines[1:])
                if value is not None:
                    fields[first] = value
            continue

    # --- Second pass: proximity matching for lone box numbers ---
    # Use word-level extraction for precise positioning (avoids block merging)
    if lone_box_blocks:
        doc2 = fitz.open(file_path)
        words = doc2[0].get_text("words")  # (x0, y0, x1, y1, word, block, line, word_n)
        doc2.close()

        # Build list of numeric words (potential values)
        numeric_words: list[tuple] = []  # (value, x0, y0, x1, y1)
        for w in words:
            word_text = w[4].replace(",", "").strip()
            if not word_text:
                continue
            # Skip words that are just box numbers
            if word_text in _VALID_BOX_IDS or word_text in _SKIP_BOX_IDS:
                continue
            try:
                val = float(word_text)
                if val > 1:
                    numeric_words.append((val, w[0], w[1], w[2], w[3]))
            except ValueError:
                # Check for decimal parts like ".25" — will be handled with int part
                pass

        # For each lone box, find nearest numeric word to its right on same row
        # Also handle split values: "55000" + ".25" at similar positions
        for box_id, bx0, by0, bx1, by1 in lone_box_blocks:
            if box_id in fields:
                continue
            best_val = None
            best_x = float("inf")
            for val, nx0, ny0, nx1, ny1 in numeric_words:
                y_diff = abs(by0 - ny0)
                x_dist = nx0 - bx1
                if y_diff < 5 and x_dist > 0 and x_dist < best_x:
                    best_x = x_dist
                    best_val = val
                    best_nx1 = nx1
                    best_ny0 = ny0
            if best_val is not None:
                # Check for a decimal part word immediately after (e.g., ".25")
                for w in words:
                    word_text = w[4].strip()
                    if word_text.startswith(".") and len(word_text) <= 4:
                        wy_diff = abs(best_ny0 - w[1])
                        wx_diff = w[0] - best_nx1
                        if wy_diff < 5 and 0 <= wx_diff < 15:
                            try:
                                best_val = best_val + float(word_text)
                            except ValueError:
                                pass
                            break
                fields[box_id] = best_val

    if employer_name:
        fields["employer_name"] = employer_name
    if tax_year:
        fields["tax_year"] = tax_year
    if province_code:
        fields["province_code"] = province_code

    return fields


def _parse_fields_regex(raw_text: str) -> dict:
    """Fallback: regex-based box number to value mapping from raw text.

    Less accurate than spatial extraction but works when block analysis fails.
    """
    fields = {}
    box_pattern = re.compile(r"(?:Box\s*)?(\d{2})\s*[:.]?\s*([\d,]+\.?\d*)", re.IGNORECASE)
    for m in box_pattern.finditer(raw_text):
        box_num, val_str = m.group(1), m.group(2).replace(",", "")
        try:
            fields[box_num] = float(val_str)
        except ValueError:
            pass
    year_match = re.search(r"20\d{2}", raw_text)
    if year_match:
        fields["tax_year"] = int(year_match.group())
    prov_match = re.search(r"\b(ON|BC|AB|QC|MB|SK|NS|NB|NL|PE|NT|NU|YT)\b", raw_text)
    if prov_match:
        fields["province_code"] = prov_match.group(1).upper()
    return fields


def _extract_digital_text(file_path: str) -> str:
    """Extract plain text from digital PDF using PyMuPDF."""
    try:
        import fitz
    except ImportError:
        return ""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text or ""


def _pdf_to_base64_image(
    file_path: str,
    dpi: int = 200,
    redact_pii: bool = False,
    doc_type: Optional[str] = None,
) -> Optional[str]:
    """Convert first page of a PDF to a base64-encoded PNG image.

    If redact_pii=True, blacks out PII areas before converting to image.
    doc_type controls which redaction strategy is used:
      - None: auto-detect form type from page content
      - "t4", "t4a", etc.: force a specific form config
      - Falls back to generic pattern-only redaction if form type is unrecognized
    """
    try:
        import fitz
    except ImportError:
        return None

    from services.redaction_service import redact_pdf_page_for_form

    doc = fitz.open(file_path)
    if len(doc) == 0:
        doc.close()
        return None
    page = doc[0]
    if redact_pii:
        redact_pdf_page_for_form(page, doc_type=doc_type)
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode()


def _validate_fields(fields: dict, tax_year: int = 2024) -> dict:
    """Range validation: CPP max, EI max, tax rate anomaly. Add _validation_flags and _confidence."""
    flags = []
    max_cpp = 3867.50 if tax_year <= 2024 else 4034.10
    max_ei = 1049.12 if tax_year <= 2024 else 1077.48
    box_16 = fields.get("16") or fields.get(16) or 0
    box_18 = fields.get("18") or fields.get(18) or 0
    box_14 = fields.get("14") or fields.get(14) or 0
    box_22 = fields.get("22") or fields.get(22) or 0
    if box_16 > max_cpp:
        flags.append("CPP_EXCEEDS_MAXIMUM")
    if box_18 > max_ei:
        flags.append("EI_EXCEEDS_MAXIMUM")
    if box_14 and box_14 > 0 and box_22 is not None:
        effective_rate = box_22 / box_14
        if effective_rate > 0.55 or effective_rate < 0.05:
            flags.append("TAX_RATE_ANOMALY")
    fields["_validation_flags"] = flags
    fields["_confidence"] = max(0.0, 1.0 - len(flags) * 0.15)
    return fields


def extract_t4(
    file_path: str,
    *,
    use_vision_fallback: bool = True,
    redact_before_vision: bool = True,
) -> dict:
    """Main pipeline: spatial extraction → regex fallback → optional vision fallback → redact → validate."""
    from services.redaction_service import redact_pii

    path = Path(file_path)
    if not path.exists():
        return {"error": "File not found", "_confidence": 0}

    suffix = path.suffix.lower()
    is_image = suffix in (".png", ".jpg", ".jpeg")

    # For image files, go directly to vision extraction
    if is_image:
        if not use_vision_fallback:
            return {"error": "Image files require vision extraction", "_confidence": 0}
        if redact_before_vision:
            from services.redaction_service import redact_image
            _form_id, img_b64 = redact_image(file_path)
        else:
            img_bytes = path.read_bytes()
            img_b64 = base64.b64encode(img_bytes).decode()
        from services.llm_service import extract_via_vision
        vision_result = extract_via_vision(img_b64, "image/png")
        return extract_t4_vision_result(vision_result)

    # For PDFs: try spatial extraction first
    raw_fields = _parse_fields_spatial(file_path)

    # If spatial extraction found fewer than 3 box values, try regex fallback
    box_count = sum(1 for k in raw_fields if k.isdigit() or (len(k) <= 3 and k[:-1].isdigit()))
    if box_count < 3:
        raw_text = _extract_digital_text(file_path)
        regex_fields = _parse_fields_regex(raw_text)
        regex_box_count = sum(1 for k in regex_fields if isinstance(k, str) and k.isdigit())
        if regex_box_count > box_count:
            raw_fields = regex_fields

    # If still very few fields and vision is enabled, try GPT-4o Vision
    box_count = sum(1 for k in raw_fields if isinstance(k, str) and (k.isdigit() or (len(k) <= 3 and k[:-1].isdigit())))
    if use_vision_fallback and box_count < 3:
        img_b64 = _pdf_to_base64_image(file_path, redact_pii=redact_before_vision)
        if img_b64:
            from services.llm_service import extract_via_vision
            vision_result = extract_via_vision(img_b64, "image/png")
            vision_validated = extract_t4_vision_result(vision_result)
            # Use vision result if it has more fields
            vision_box_count = sum(1 for k in vision_validated if isinstance(k, str) and k.isdigit())
            if vision_box_count > box_count:
                return vision_validated

    if not raw_fields:
        raw_text = _extract_digital_text(file_path)
        if raw_text.strip():
            raw_fields["_raw_preview"] = raw_text[:500]

    redacted = redact_pii(raw_fields)
    tax_year = redacted.get("tax_year") or 2024
    validated = _validate_fields(redacted, tax_year)
    return validated


def extract_t4_vision_result(vision_json: dict) -> dict:
    """Apply validation and confidence to result from GPT-4o Vision."""
    tax_year = vision_json.get("tax_year") or 2024
    return _validate_fields(dict(vision_json), tax_year)


# --- Multi-document support ---

# T5 box labels (Statement of Investment Income)
_T5_BOX_LABELS = {
    "13": "Interest from Canadian sources",
    "14": "Other income from Canadian sources",
    "18": "Capital gains dividends",
    "24": "Eligible dividends",
    "25": "Eligible dividends amount taxable",
    "26": "Other than eligible dividends",
    "10": "Actual amount of eligible dividends",
    "11": "Taxable amount of eligible dividends",
    "12": "Actual amount of other dividends",
}


def detect_document_type(file_path: str) -> str:
    """Detect the type of tax document from its text content.

    Returns: "T4", "T5", "T2202", "NOA", or "UNKNOWN".
    """
    text = _extract_digital_text(file_path).upper()
    if not text:
        return "UNKNOWN"
    # Check specific form identifiers
    if "T4A" in text:
        return "T4"  # T4A treated as T4 variant
    if "STATEMENT OF INVESTMENT INCOME" in text or "T5 " in text[:500]:
        return "T5"
    if "T2202" in text or "TUITION" in text and "EDUCATION" in text:
        return "T2202"
    if "NOTICE OF ASSESSMENT" in text or "NOTICE OF REASSESSMENT" in text:
        return "NOA"
    if "T4 " in text[:500] or "STATEMENT OF REMUNERATION" in text:
        return "T4"
    return "UNKNOWN"


def extract_t5(file_path: str) -> dict:
    """Extract T5 (Statement of Investment Income) fields using spatial analysis."""
    try:
        import fitz
    except ImportError:
        return {"error": "PyMuPDF not installed", "doc_type": "T5"}

    doc = fitz.open(file_path)
    if len(doc) == 0:
        doc.close()
        return {"error": "Empty document", "doc_type": "T5"}

    page = doc[0]
    blocks = page.get_text("blocks")
    doc.close()

    fields: dict = {"doc_type": "T5"}
    tax_year = None

    for block in blocks:
        if block[6] != 0:
            continue
        text = block[4].strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            continue

        first = lines[0]

        # Year detection
        if re.match(r"^20\d{2}$", first):
            tax_year = int(first)
            continue

        # T5 box extraction
        if first in _T5_BOX_LABELS and len(lines) >= 2:
            value = _parse_value_from_lines(lines[1:])
            if value is not None:
                fields[first] = value

    if tax_year:
        fields["tax_year"] = tax_year

    from services.redaction_service import redact_pii
    return redact_pii(fields)


def extract_t2202(file_path: str) -> dict:
    """Extract T2202 (Tuition and Education Amounts Certificate) fields."""
    try:
        import fitz
    except ImportError:
        return {"error": "PyMuPDF not installed", "doc_type": "T2202"}

    doc = fitz.open(file_path)
    if len(doc) == 0:
        doc.close()
        return {"error": "Empty document", "doc_type": "T2202"}

    page = doc[0]
    blocks = page.get_text("blocks")
    doc.close()

    fields: dict = {"doc_type": "T2202"}
    tax_year = None

    # T2202 key boxes:
    # Box A: Eligible tuition fees
    # Box B: Part-time months (or months in full-time)
    # Box C: Full-time months
    t2202_boxes = {"A", "B", "C"}

    for block in blocks:
        if block[6] != 0:
            continue
        text = block[4].strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            continue

        first = lines[0]

        # Year detection
        if re.match(r"^20\d{2}$", first):
            tax_year = int(first)
            continue

        # Look for tuition amount patterns
        if "tuition" in first.lower() and "eligible" in first.lower():
            for ln in lines[1:]:
                val = _parse_value_from_lines([ln])
                if val is not None and val > 0:
                    fields["eligible_tuition_fees"] = val
                    break
            continue

        # Box-based extraction
        if first.upper() in t2202_boxes and len(lines) >= 2:
            value = _parse_value_from_lines(lines[1:])
            if value is not None:
                if first.upper() == "A":
                    fields["eligible_tuition_fees"] = value
                elif first.upper() == "B":
                    fields["part_time_months"] = value
                elif first.upper() == "C":
                    fields["full_time_months"] = value

        # Institution name
        if "institution" in first.lower() or "university" in first.lower() or "college" in first.lower():
            for ln in lines:
                if not any(kw in ln.lower() for kw in ["institution", "box", "name"]):
                    fields["institution_name"] = ln
                    break

    if tax_year:
        fields["tax_year"] = tax_year

    # If we didn't get tuition fees from structured extraction, try vision
    if "eligible_tuition_fees" not in fields:
        img_b64 = _pdf_to_base64_image(file_path, redact_pii=True)
        if img_b64:
            from services.llm_service import extract_via_vision
            vision_result = extract_via_vision(img_b64, "image/png")
            if vision_result.get("eligible_tuition_fees"):
                fields["eligible_tuition_fees"] = vision_result["eligible_tuition_fees"]
            if vision_result.get("institution_name"):
                fields.setdefault("institution_name", vision_result["institution_name"])
            if vision_result.get("tax_year"):
                fields.setdefault("tax_year", vision_result["tax_year"])

    from services.redaction_service import redact_pii
    return redact_pii(fields)


def extract_noa(file_path: str) -> dict:
    """Extract Notice of Assessment / Reassessment fields."""
    try:
        import fitz
    except ImportError:
        return {"error": "PyMuPDF not installed", "doc_type": "NOA"}

    doc = fitz.open(file_path)
    if len(doc) == 0:
        doc.close()
        return {"error": "Empty document", "doc_type": "NOA"}

    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    fields: dict = {"doc_type": "NOA"}

    # Year detection
    year_match = re.search(r"tax year\s*(20\d{2})", text, re.IGNORECASE)
    if year_match:
        fields["tax_year"] = int(year_match.group(1))
    else:
        year_match = re.search(r"20\d{2}", text[:200])
        if year_match:
            fields["tax_year"] = int(year_match.group())

    # Key NOA fields
    patterns = [
        (r"total\s+income[:\s]*\$?([\d,]+\.?\d*)", "total_income"),
        (r"net\s+income[:\s]*\$?([\d,]+\.?\d*)", "net_income"),
        (r"taxable\s+income[:\s]*\$?([\d,]+\.?\d*)", "taxable_income"),
        (r"total\s+(?:payable|tax)[:\s]*\$?([\d,]+\.?\d*)", "total_tax_payable"),
        (r"total\s+credits[:\s]*\$?([\d,]+\.?\d*)", "total_credits"),
        (r"refund[:\s]*\$?([\d,]+\.?\d*)", "refund"),
        (r"balance\s+owing[:\s]*\$?([\d,]+\.?\d*)", "balance_owing"),
        (r"RRSP\s+(?:deduction\s+)?limit[:\s]*\$?([\d,]+\.?\d*)", "rrsp_deduction_limit"),
        (r"TFSA\s+(?:contribution\s+)?room[:\s]*\$?([\d,]+\.?\d*)", "tfsa_contribution_room"),
    ]

    for pattern, field_name in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                fields[field_name] = float(match.group(1).replace(",", ""))
            except ValueError:
                pass

    from services.redaction_service import redact_pii
    return redact_pii(fields)


def extract_generic(file_path: str) -> dict:
    """Fallback extraction using GPT-4o Vision for unknown document types."""
    img_b64 = _pdf_to_base64_image(file_path, redact_pii=True)
    if not img_b64:
        raw_text = _extract_digital_text(file_path)
        return {"_raw_preview": raw_text[:500], "doc_type": "UNKNOWN"} if raw_text else {"error": "Cannot read document"}
    from services.llm_service import extract_via_vision
    result = extract_via_vision(img_b64, "image/png")
    result["doc_type"] = "GENERIC"
    return result


def extract_document(file_path: str, **kwargs) -> dict:
    """Unified extraction entry point: auto-detect document type and route to appropriate extractor."""
    path = Path(file_path)
    if not path.exists():
        return {"error": "File not found", "_confidence": 0}

    suffix = path.suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg"):
        result = extract_t4(file_path, **kwargs)
        result["doc_type"] = "T4"
        return result

    doc_type = detect_document_type(file_path)
    if doc_type == "T5":
        return extract_t5(file_path)
    elif doc_type == "T2202":
        return extract_t2202(file_path)
    elif doc_type == "NOA":
        return extract_noa(file_path)
    elif doc_type == "T4":
        result = extract_t4(file_path, **kwargs)
        result["doc_type"] = "T4"
        return result
    else:
        result = extract_generic(file_path)
        result["doc_type"] = doc_type if doc_type != "UNKNOWN" else "GENERIC"
        return result
