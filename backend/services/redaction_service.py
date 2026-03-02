"""
PII redaction — deterministic masking before any external API or storage.
Two modes:
  1. Text/dict redaction: regex replacement for extracted data (before DB storage or LLM calls)
  2. PDF page redaction: black-out PII regions on any document page (before vision model)

Supported PII types:
  - SIN (Social Insurance Number)
  - Credit card numbers
  - Phone numbers (North American)
  - Email addresses
  - Canadian postal codes
  - Dates of birth (various formats)
  - Driver's licence numbers (Canadian provinces)
  - Canadian passport numbers
  - Bank transit/account numbers
  - Street addresses (section-based on known form layouts)

Supported form types (auto-detected):
  - T4: Statement of Remuneration Paid
  - T4A: Statement of Pension, Retirement, Annuity, and Other Income
  - T5: Statement of Investment Income
  - T3: Statement of Trust Income Allocations and Designations
  - T2202: Tuition and Enrolment Certificate
  - T5007: Statement of Benefits
  - RRSP: RRSP/PRPP Contribution Receipt
  - NOA: Notice of Assessment
  - Bank statement (generic)
  - Pay stub (generic)
"""
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Compiled PII patterns — shared by text redaction and PDF redaction
# ---------------------------------------------------------------------------

_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # SIN: 123 456 789 or 123-456-789 or 123456789
    (re.compile(r"\b\d{3}[\s-]\d{3}[\s-]\d{3}\b"), "[SIN-REDACTED]"),
    (re.compile(r"\b\d{9}\b"), "[SIN-REDACTED]"),

    # Credit card: 4 groups of 4 digits (Visa, MC, Amex variants)
    (re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b"), "[CC-REDACTED]"),
    (re.compile(r"\b\d{4}[\s-]\d{6}[\s-]\d{5}\b"), "[CC-REDACTED]"),  # Amex: 4-6-5
    (re.compile(r"\b\d{16}\b"), "[CC-REDACTED]"),

    # Phone numbers: (416) 555-1234, 416-555-1234, 416.555.1234
    (re.compile(r"\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"), "[PHONE-REDACTED]"),

    # Email addresses
    (re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"), "[EMAIL-REDACTED]"),

    # Canadian postal code: A1A 1A1 or A1A1A1
    (re.compile(r"\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b", re.IGNORECASE), "[POSTAL-REDACTED]"),

    # Street address: number + street name + suffix (e.g. 123 Main Street, 45 Oak Ave)
    (re.compile(
        r"\b\d{1,5}\s+[\w\s]{1,40}\b(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|"
        r"Crescent|Cres|Court|Ct|Way|Lane|Ln|Circle|Cir|Place|Pl|Terrace|Ter|"
        r"Trail|Trl|Highway|Hwy|Parkway|Pkwy)\b\.?",
        re.IGNORECASE,
    ), "[ADDRESS-REDACTED]"),

    # City + Province: Toronto, ON  /  Vancouver, BC  /  Montreal QC  etc.
    (re.compile(
        r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*[,\s]+(?:ON|QC|BC|AB|MB|SK|NS|NB|PE|NL|YT|NT|NU|"
        r"Ontario|Quebec|British Columbia|Alberta|Manitoba|Saskatchewan|"
        r"Nova Scotia|New Brunswick|Prince Edward Island|"
        r"Newfoundland and Labrador|Yukon|Northwest Territories|Nunavut)\b",
        re.IGNORECASE,
    ), "[CITY-PROV-REDACTED]"),

    # Apartment/Unit/Suite prefix: Unit 5, Apt 12B, Suite 300
    (re.compile(
        r"\b(?:Unit|Apt|Apartment|Suite|Ste|#)\s*\d+[A-Za-z]?\b",
        re.IGNORECASE,
    ), "[UNIT-REDACTED]"),

    # DOB: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY
    (re.compile(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b"), "[DOB-REDACTED]"),
    (re.compile(r"\b\d{2}[-/]\d{2}[-/]\d{4}\b"), "[DOB-REDACTED]"),

    # Canadian driver's licence (Ontario format: A1234-56789-01234)
    (re.compile(r"\b[A-Z]\d{4}[-]?\d{5}[-]?\d{5}\b"), "[DL-REDACTED]"),
    # BC/Alberta: 7-digit numeric
    (re.compile(r"\b\d{7}\b"), "[ID-REDACTED]"),

    # Canadian passport: 2 letters + 6 digits
    (re.compile(r"\b[A-Z]{2}\d{6}\b"), "[PASSPORT-REDACTED]"),

    # Bank transit-institution-account: 12345-001-1234567
    (re.compile(r"\b\d{5}[-]\d{3}[-]\d{5,12}\b"), "[BANK-REDACTED]"),
]

# Patterns used only for PDF word-level scanning (standalone long numbers)
_PDF_EXTRA_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d{8,9}$"),    # SIN without separators
    re.compile(r"^\d{16}$"),     # Credit card without separators
]

# Dict keys that indicate PII content (used in dict redaction)
_PII_KEYS = {
    "sin", "name", "employee_name", "address", "street", "city",
    "postal_code", "date_of_birth", "dob", "phone", "email",
    "driver_licence", "drivers_licence", "licence_number", "license_number",
    "passport", "passport_number", "bank_account", "account_number",
    "transit_number", "social_insurance_number",
}


# ---------------------------------------------------------------------------
# Form-specific redaction configs
# ---------------------------------------------------------------------------

@dataclass
class FormRedactionConfig:
    """Configuration for form-specific PII section redaction.

    Attributes:
        form_id: Short identifier (e.g. "t4", "t4a", "bank_statement").
        detect_keywords: Text that must appear on the page to identify this form type.
            Any ONE match triggers detection.
        pii_section_headers: Lowercase strings that mark the START of a PII section.
            When a text block contains any of these, all subsequent blocks are redacted
            until an end marker or max_section_depth is reached.
        pii_section_end_markers: Lowercase strings that mark the END of a PII section.
        max_section_depth: Max vertical distance (PDF points) from section header before
            auto-closing the section. Prevents runaway redaction.
        pii_label_keywords: Standalone label text to always redact (e.g. "social insurance number").
            These are redacted by substring match regardless of section boundaries.
    """
    form_id: str
    detect_keywords: list[str]
    pii_section_headers: list[str] = field(default_factory=list)
    pii_section_end_markers: list[str] = field(default_factory=list)
    max_section_depth: float = 120.0
    pii_label_keywords: list[str] = field(default_factory=list)


# -- Registry of all supported form types --

FORM_CONFIGS: list[FormRedactionConfig] = [
    # T4 — Statement of Remuneration Paid
    FormRedactionConfig(
        form_id="t4",
        detect_keywords=["statement of remuneration paid", "état de la rémunération payée", "t4 ("],
        pii_section_headers=[
            "employee's name", "nom et adresse de l'employé",
            "employee's address", "adresse de l'employé",
            "last name", "nom de famille", "first name", "prénom",
            "name and address", "nom et adresse",
        ],
        pii_section_end_markers=["other information", "autres renseignements"],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
            "numéro d'assurance sociale",
        ],
    ),

    # T4A — Statement of Pension, Retirement, Annuity, and Other Income
    FormRedactionConfig(
        form_id="t4a",
        detect_keywords=["statement of pension", "état du revenu de pension", "t4a ("],
        pii_section_headers=[
            "recipient's name", "nom du bénéficiaire",
            "last name", "nom de famille", "first name", "prénom",
            "recipient's address", "adresse du bénéficiaire",
        ],
        pii_section_end_markers=["other information", "autres renseignements", "footnotes"],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # T5 — Statement of Investment Income
    FormRedactionConfig(
        form_id="t5",
        detect_keywords=["statement of investment income", "état des revenus de placements", "t5 ("],
        pii_section_headers=[
            "recipient's name", "nom du bénéficiaire",
            "last name", "nom de famille",
            "recipient's address", "adresse du bénéficiaire",
        ],
        pii_section_end_markers=["other information", "autres renseignements", "footnotes"],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # T3 — Statement of Trust Income Allocations and Designations
    FormRedactionConfig(
        form_id="t3",
        detect_keywords=["statement of trust income", "état des revenus de fiducie", "t3 ("],
        pii_section_headers=[
            "recipient's name", "nom du bénéficiaire",
            "last name", "nom de famille",
            "recipient's address",
        ],
        pii_section_end_markers=["footnotes", "autres renseignements"],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # T2202 — Tuition and Enrolment Certificate
    FormRedactionConfig(
        form_id="t2202",
        detect_keywords=["tuition and enrolment", "certificat pour frais de scolarité", "t2202"],
        pii_section_headers=[
            "student's name", "nom de l'étudiant",
            "last name", "nom de famille", "first name",
            "student's address", "adresse de l'étudiant",
        ],
        pii_section_end_markers=["eligible tuition", "frais de scolarité admissibles"],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # T5007 — Statement of Benefits
    FormRedactionConfig(
        form_id="t5007",
        detect_keywords=["statement of benefits", "état des prestations", "t5007"],
        pii_section_headers=[
            "recipient's name", "nom du bénéficiaire",
            "last name", "nom de famille",
            "recipient's address",
        ],
        pii_section_end_markers=["other information", "autres renseignements"],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # RRSP / PRPP Contribution Receipt
    FormRedactionConfig(
        form_id="rrsp",
        detect_keywords=["rrsp contribution receipt", "reçu de cotisation reer", "prpp", "rpac"],
        pii_section_headers=[
            "contributor", "cotisant",
            "annuitant", "rentier",
            "last name", "nom de famille", "first name",
        ],
        pii_section_end_markers=["contribution amount", "montant de la cotisation", "other information"],
        max_section_depth=100.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # Notice of Assessment (CRA)
    FormRedactionConfig(
        form_id="noa",
        detect_keywords=["notice of assessment", "avis de cotisation"],
        pii_section_headers=[
            "name and address", "nom et adresse",
            "mailing address", "adresse postale",
        ],
        pii_section_end_markers=["tax year", "année d'imposition", "total income", "revenu total"],
        max_section_depth=150.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
        ],
    ),

    # Bank Statement (generic)
    FormRedactionConfig(
        form_id="bank_statement",
        detect_keywords=["account statement", "bank statement", "relevé de compte", "statement period"],
        pii_section_headers=[
            "account holder", "titulaire du compte",
            "mailing address", "adresse postale",
            "customer name", "nom du client",
        ],
        pii_section_end_markers=[
            "account summary", "sommaire du compte",
            "opening balance", "solde d'ouverture",
            "transaction", "date",
        ],
        max_section_depth=150.0,
        pii_label_keywords=[
            "account number", "numéro de compte",
            "transit", "institution",
        ],
    ),

    # Pay Stub (generic)
    FormRedactionConfig(
        form_id="pay_stub",
        detect_keywords=["pay stub", "pay statement", "bulletin de paie", "relevé de paie", "pay period"],
        pii_section_headers=[
            "employee name", "nom de l'employé",
            "employee address", "adresse de l'employé",
            "last name", "nom de famille",
        ],
        pii_section_end_markers=[
            "earnings", "revenus", "gross pay", "salaire brut",
            "current", "year to date", "ytd",
        ],
        max_section_depth=120.0,
        pii_label_keywords=[
            "social insurance", "assurance sociale",
            "employee id", "numéro d'employé",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Text / dict redaction (Layer 2 — for extracted data)
# ---------------------------------------------------------------------------

def redact_pii(text_or_dict: str | dict) -> str | dict:
    """Main entry point. If str: apply regex redaction. If dict: strip PII keys + redact values."""
    if isinstance(text_or_dict, str):
        return _redact_text(text_or_dict)
    if isinstance(text_or_dict, dict):
        return _redact_dict(text_or_dict)
    return text_or_dict


def _redact_text(text: str) -> str:
    """Apply all PII regex patterns to a text string."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_dict(data: dict) -> dict:
    """Strip PII keys entirely; redact PII patterns in remaining string values.
    Employer name retained (business entity)."""
    out = {}
    for k, v in data.items():
        key_lower = k.lower().replace(" ", "_")
        if key_lower in _PII_KEYS:
            continue
        if isinstance(v, str):
            out[k] = _redact_text(v)
        elif isinstance(v, (int, float)) or v is None:
            out[k] = v
        elif isinstance(v, dict):
            out[k] = _redact_dict(v)
        elif isinstance(v, list):
            out[k] = [_redact_pii_item(x) for x in v]
        else:
            out[k] = v
    return out


def _redact_pii_item(x: Any) -> Any:
    if isinstance(x, str):
        return _redact_text(x)
    if isinstance(x, dict):
        return _redact_dict(x)
    return x


# ---------------------------------------------------------------------------
# PDF page redaction (Layer 1 — for images sent to vision model)
# ---------------------------------------------------------------------------

def redact_pdf_page(page, *, preserve_keywords: Optional[set[str]] = None) -> None:
    """Generic PII redaction on any PDF page using word-level pattern scanning.

    Scans every word on the page against all PII regex patterns. When a match
    is found, draws a black redaction rectangle over those words. Works on any
    document layout — no form-specific knowledge required.
    """
    import fitz

    preserve = preserve_keywords or set()

    words = page.get_text("words")
    # words = list of (x0, y0, x1, y1, word, block_no, line_no, word_no)

    lines: dict[tuple[int, int], list] = {}
    for w in words:
        key = (w[5], w[6])
        lines.setdefault(key, []).append(w)

    for key in lines:
        lines[key].sort(key=lambda w: w[0])

    redact_rects: list = []

    for line_key, line_words in lines.items():
        line_text = ""
        char_to_word_idx: list[int] = []

        for i, w in enumerate(line_words):
            word_text = w[4]
            if line_text:
                line_text += " "
                char_to_word_idx.append(i)
            line_text += word_text
            char_to_word_idx.extend([i] * len(word_text))

        for pattern, _replacement in _PII_PATTERNS:
            for m in pattern.finditer(line_text):
                matched_text = m.group()
                if matched_text.lower() in {p.lower() for p in preserve}:
                    continue
                start_idx = m.start()
                end_idx = m.end() - 1
                if start_idx >= len(char_to_word_idx) or end_idx >= len(char_to_word_idx):
                    continue
                first_word = char_to_word_idx[start_idx]
                last_word = char_to_word_idx[end_idx]
                x0 = min(line_words[j][0] for j in range(first_word, last_word + 1))
                y0 = min(line_words[j][1] for j in range(first_word, last_word + 1))
                x1 = max(line_words[j][2] for j in range(first_word, last_word + 1))
                y1 = max(line_words[j][3] for j in range(first_word, last_word + 1))
                redact_rects.append(fitz.Rect(x0, y0, x1, y1))

        for i, w in enumerate(line_words):
            for extra_pat in _PDF_EXTRA_PATTERNS:
                if extra_pat.match(w[4]):
                    redact_rects.append(fitz.Rect(w[0], w[1], w[2], w[3]))

    for rect in redact_rects:
        page.add_redact_annot(rect, fill=(0, 0, 0))

    if redact_rects:
        page.apply_redactions()


def detect_form_type(page) -> Optional[FormRedactionConfig]:
    """Auto-detect the form type from a PDF page's text content.

    Scans all text on the page and matches against each form config's
    detect_keywords. Returns the first matching config, or None if no
    form type is recognized.
    """
    full_text = page.get_text().lower()
    for config in FORM_CONFIGS:
        if any(kw in full_text for kw in config.detect_keywords):
            return config
    return None


def _apply_form_sections(page, config: FormRedactionConfig) -> None:
    """Apply section-based redaction using a FormRedactionConfig.

    1. Scans blocks for PII section headers → redacts all blocks until end marker
    2. Redacts blocks containing PII label keywords anywhere on the page
    """
    import fitz

    blocks = page.get_text("blocks")
    redact_rects: list = []

    in_pii_section = False
    section_y_start = 0.0

    for block in blocks:
        if block[6] != 0:
            continue

        text_lower = block[4].strip().lower()
        y0 = block[1]

        # Check if this block starts a PII section
        if any(kw in text_lower for kw in config.pii_section_headers):
            in_pii_section = True
            section_y_start = y0
            # Redact the header block too — it may contain the PII value
            # (e.g. "Employee's name\nJohn Smith" in one block)
            redact_rects.append(fitz.Rect(block[0], block[1], block[2], block[3]))
            continue

        # If inside a PII section, redact until end marker or max depth
        if in_pii_section and y0 >= section_y_start:
            if any(kw in text_lower for kw in config.pii_section_end_markers):
                in_pii_section = False
                continue
            if y0 - section_y_start > config.max_section_depth:
                in_pii_section = False
                continue
            redact_rects.append(fitz.Rect(block[0], block[1], block[2], block[3]))

    # Redact PII label keywords anywhere on the page
    for block in blocks:
        if block[6] != 0:
            continue
        text_lower = block[4].strip().lower()
        if any(kw in text_lower for kw in config.pii_label_keywords):
            redact_rects.append(fitz.Rect(block[0], block[1], block[2], block[3]))

    for rect in redact_rects:
        page.add_redact_annot(rect, fill=(0, 0, 0))

    if redact_rects:
        page.apply_redactions()


def redact_pdf_page_for_form(page, doc_type: Optional[str] = None) -> str:
    """Full PDF page redaction: generic patterns + form-specific sections.

    Args:
        page: A PyMuPDF Page object.
        doc_type: Optional form type override (e.g. "t4", "bank_statement").
            If None, auto-detects from the page content.

    Returns:
        The detected/used form_id string (e.g. "t4", "generic").
    """
    # Step 1: Always run generic pattern-based redaction
    redact_pdf_page(page)

    # Step 2: Determine form config
    config: Optional[FormRedactionConfig] = None
    if doc_type:
        config = next((c for c in FORM_CONFIGS if c.form_id == doc_type), None)
    else:
        config = detect_form_type(page)

    # Step 3: Apply form-specific section redaction if recognized
    if config:
        _apply_form_sections(page, config)
        return config.form_id

    return "generic"


# Backward-compatible aliases
def redact_pdf_page_t4(page) -> None:
    """T4-specific redaction. Alias for redact_pdf_page_for_form(page, 't4')."""
    redact_pdf_page_for_form(page, doc_type="t4")


# ---------------------------------------------------------------------------
# Image redaction (Layer 1b — for images sent to vision model)
# ---------------------------------------------------------------------------

def _detect_form_type_from_text(full_text: str) -> Optional[FormRedactionConfig]:
    """Auto-detect form type from raw OCR text (same logic as detect_form_type but for strings)."""
    text_lower = full_text.lower()
    for config in FORM_CONFIGS:
        if any(kw in text_lower for kw in config.detect_keywords):
            return config
    return None


def redact_image(
    image_path: str,
    *,
    doc_type: Optional[str] = None,
    output_path: Optional[str] = None,
) -> tuple[str, str]:
    """Redact PII from an image file (PNG/JPEG) using Tesseract OCR.

    Uses Tesseract to get word-level bounding boxes, then applies the same
    PII pattern matching + form-specific section redaction as the PDF pipeline.
    Draws black rectangles over detected PII using Pillow.

    Args:
        image_path: Path to the input image file.
        doc_type: Optional form type override. If None, auto-detects.
        output_path: Optional path to save the redacted image. If None,
            returns the redacted image bytes without saving.

    Returns:
        Tuple of (form_id, redacted_image_base64).
    """
    import base64
    from io import BytesIO

    import pytesseract
    from PIL import Image, ImageDraw

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Get word-level OCR data from Tesseract
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    n_words = len(ocr_data["text"])

    # Build word list: (x0, y0, x1, y1, word, block_num, line_num)
    words = []
    for i in range(n_words):
        word = ocr_data["text"][i].strip()
        if not word:
            continue
        x = ocr_data["left"][i]
        y = ocr_data["top"][i]
        w = ocr_data["width"][i]
        h = ocr_data["height"][i]
        block = ocr_data["block_num"][i]
        line = ocr_data["line_num"][i]
        words.append((x, y, x + w, y + h, word, block, line))

    redact_rects: list[tuple[int, int, int, int]] = []

    # --- Step 1: Generic pattern-based redaction (line-level) ---
    lines: dict[tuple[int, int], list] = {}
    for w in words:
        key = (w[5], w[6])  # (block_num, line_num)
        lines.setdefault(key, []).append(w)

    for key in lines:
        lines[key].sort(key=lambda w: w[0])  # sort by x position

    for line_key, line_words in lines.items():
        line_text = ""
        char_to_word_idx: list[int] = []

        for i, w in enumerate(line_words):
            word_text = w[4]
            if line_text:
                line_text += " "
                char_to_word_idx.append(i)
            line_text += word_text
            char_to_word_idx.extend([i] * len(word_text))

        # Match PII patterns against reconstructed line text
        for pattern, _replacement in _PII_PATTERNS:
            for m in pattern.finditer(line_text):
                start_idx = m.start()
                end_idx = m.end() - 1
                if start_idx >= len(char_to_word_idx) or end_idx >= len(char_to_word_idx):
                    continue
                first_word = char_to_word_idx[start_idx]
                last_word = char_to_word_idx[end_idx]
                x0 = min(line_words[j][0] for j in range(first_word, last_word + 1))
                y0 = min(line_words[j][1] for j in range(first_word, last_word + 1))
                x1 = max(line_words[j][2] for j in range(first_word, last_word + 1))
                y1 = max(line_words[j][3] for j in range(first_word, last_word + 1))
                redact_rects.append((x0, y0, x1, y1))

        # Check individual words against extra patterns (standalone long numbers)
        for w in line_words:
            for extra_pat in _PDF_EXTRA_PATTERNS:
                if extra_pat.match(w[4]):
                    redact_rects.append((w[0], w[1], w[2], w[3]))

    # --- Step 2: Form-specific section-based redaction ---
    # Tesseract often merges left-column PII and right-column financial data
    # into the same line/block. We use LINE-level grouping with X-position
    # awareness: only redact words in the LEFT half of the page (where PII
    # like name, address, SIN sits) while preserving the RIGHT half (financial boxes).
    full_text = " ".join(w[4] for w in words)
    config: Optional[FormRedactionConfig] = None
    if doc_type:
        config = next((c for c in FORM_CONFIGS if c.form_id == doc_type), None)
    else:
        config = _detect_form_type_from_text(full_text)

    form_id = config.form_id if config else "generic"

    if config:
        img_width = img.width
        # PII sections (name, address) occupy the left portion of tax forms.
        # Use 55% of page width as the boundary to avoid clipping financial boxes.
        pii_x_boundary = img_width * 0.55

        # Group words into lines by (block_num, par_num, line_num)
        ocr_lines: dict[tuple[int, int], list] = {}
        for i in range(n_words):
            word = ocr_data["text"][i].strip()
            if not word:
                continue
            key = (ocr_data["block_num"][i], ocr_data["line_num"][i])
            x = ocr_data["left"][i]
            y = ocr_data["top"][i]
            w = ocr_data["width"][i]
            h = ocr_data["height"][i]
            ocr_lines.setdefault(key, []).append((x, y, x + w, y + h, word))

        # Sort lines by y-position
        sorted_lines = []
        for line_key, lw in ocr_lines.items():
            lw.sort(key=lambda w: w[0])
            line_text = " ".join(w[4] for w in lw)
            y_min = min(w[1] for w in lw)
            sorted_lines.append((y_min, line_text, lw))
        sorted_lines.sort(key=lambda x: x[0])

        in_pii_section = False
        section_y_start = 0.0
        # Scale max_section_depth for image pixel coords (~2.5x PDF points)
        max_depth = config.max_section_depth * 2.5

        for y_min, line_text, line_words in sorted_lines:
            text_lower = line_text.lower()

            # Check if this line contains a PII section header
            if any(kw in text_lower for kw in config.pii_section_headers):
                in_pii_section = True
                section_y_start = y_min
                # Redact the header line too — may contain the actual PII value
                for w in line_words:
                    if w[0] < pii_x_boundary:
                        redact_rects.append((w[0], w[1], w[2], w[3]))
                continue

            # Check for section end markers
            if in_pii_section:
                if any(kw in text_lower for kw in config.pii_section_end_markers):
                    in_pii_section = False
                    continue
                if y_min - section_y_start > max_depth:
                    in_pii_section = False
                    continue

                # Redact only LEFT-SIDE words in the PII section
                for w in line_words:
                    if w[0] < pii_x_boundary:
                        redact_rects.append((w[0], w[1], w[2], w[3]))

        # Redact PII label keywords — word-level, left side only
        for y_min, line_text, line_words in sorted_lines:
            text_lower = line_text.lower()
            if any(kw in text_lower for kw in config.pii_label_keywords):
                for w in line_words:
                    if w[0] < pii_x_boundary:
                        redact_rects.append((w[0], w[1], w[2], w[3]))

    # --- Step 3: Draw black rectangles ---
    for rect in redact_rects:
        draw.rectangle(rect, fill=(0, 0, 0))

    # Save or encode
    if output_path:
        img.save(output_path)

    buf = BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return form_id, img_b64
