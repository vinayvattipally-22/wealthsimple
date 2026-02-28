"""Tests for OCR spatial extraction on original and generated T4 PDFs."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ocr_service import _parse_fields_spatial, _parse_fields_regex, _validate_fields

# Paths relative to backend/
ORIGINAL_PDF = os.path.join(os.path.dirname(__file__), "..", "..", "T4_edited.pdf")
GENERATED_PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "test_data")


class TestSpatialExtraction:
    """Test _parse_fields_spatial on real PDFs."""

    @pytest.mark.skipif(not os.path.exists(ORIGINAL_PDF), reason="Original T4 PDF not available")
    def test_original_pdf_extracts_key_boxes(self):
        fields = _parse_fields_spatial(ORIGINAL_PDF)
        # Must extract the 4 primary T4 boxes
        assert "14" in fields, "Box 14 (employment income) not extracted"
        assert "16" in fields, "Box 16 (CPP) not extracted"
        assert "18" in fields, "Box 18 (EI) not extracted"
        assert "22" in fields, "Box 22 (tax deducted) not extracted"

    @pytest.mark.skipif(not os.path.exists(ORIGINAL_PDF), reason="Original T4 PDF not available")
    def test_original_pdf_values_match(self):
        fields = _parse_fields_spatial(ORIGINAL_PDF)
        assert abs(fields["14"] - 39991.25) < 0.05
        assert abs(fields["16"] - 2171.26) < 0.05
        assert abs(fields["18"] - 663.83) < 0.05
        assert abs(fields["22"] - 1746.33) < 0.05

    @pytest.mark.skipif(not os.path.exists(ORIGINAL_PDF), reason="Original T4 PDF not available")
    def test_original_pdf_province_and_year(self):
        fields = _parse_fields_spatial(ORIGINAL_PDF)
        assert fields.get("province_code") == "ON"
        assert fields.get("tax_year") == 2024

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(GENERATED_PDF_DIR, "customer_1", "T4_2024_Thompson.pdf")),
        reason="Generated test PDFs not available",
    )
    def test_generated_pdf_extracts_key_boxes(self):
        path = os.path.join(GENERATED_PDF_DIR, "customer_1", "T4_2024_Thompson.pdf")
        fields = _parse_fields_spatial(path)
        assert "14" in fields
        assert "16" in fields
        assert "18" in fields
        assert "22" in fields

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(GENERATED_PDF_DIR, "customer_1", "T4_2024_Thompson.pdf")),
        reason="Generated test PDFs not available",
    )
    def test_generated_pdf_values_match(self):
        path = os.path.join(GENERATED_PDF_DIR, "customer_1", "T4_2024_Thompson.pdf")
        fields = _parse_fields_spatial(path)
        assert abs(fields["14"] - 55000) < 1
        assert abs(fields["16"] - 3064.25) < 0.05
        assert abs(fields["18"] - 913.00) < 0.05
        assert abs(fields["22"] - 7420.84) < 0.05

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(GENERATED_PDF_DIR, "customer_2", "T4_2020_Richardson.pdf")),
        reason="Generated test PDFs not available",
    )
    def test_multiple_years_extract(self):
        """Verify extraction across different years for customer_2."""
        expected = {
            2020: {"14": 72000, "16": 2898.00},
            2024: {"14": 95000, "16": 3867.50},
        }
        for year, vals in expected.items():
            path = os.path.join(GENERATED_PDF_DIR, "customer_2", f"T4_{year}_Richardson.pdf")
            if not os.path.exists(path):
                continue
            fields = _parse_fields_spatial(path)
            for box, exp in vals.items():
                assert abs(fields[box] - exp) < 1, f"Year {year} Box {box}: {fields.get(box)} != {exp}"


class TestRegexExtraction:
    """Test _parse_fields_regex as fallback parser."""

    def test_basic_box_parsing(self):
        text = "Box 14: 85,000.00\nBox 16: 3,867.50\nBox 22: 20,832.00"
        fields = _parse_fields_regex(text)
        assert abs(fields["14"] - 85000.0) < 0.01
        assert abs(fields["16"] - 3867.50) < 0.01
        assert abs(fields["22"] - 20832.0) < 0.01

    def test_year_extraction(self):
        text = "T4 Statement of Remuneration Paid 2024\nBox 14: 50000"
        fields = _parse_fields_regex(text)
        assert fields["tax_year"] == 2024

    def test_province_extraction(self):
        text = "Province of employment: ON\nBox 14: 50000"
        fields = _parse_fields_regex(text)
        assert fields["province_code"] == "ON"


class TestFieldValidation:
    """Test _validate_fields range checking."""

    def test_valid_fields_no_flags(self):
        fields = {"14": 55000.0, "16": 3064.25, "18": 913.00, "22": 7420.84}
        result = _validate_fields(fields, 2024)
        assert result["_validation_flags"] == []
        assert result["_confidence"] == 1.0

    def test_cpp_exceeds_maximum(self):
        fields = {"14": 55000.0, "16": 5000.0, "18": 900.0, "22": 7000.0}
        result = _validate_fields(fields, 2024)
        assert "CPP_EXCEEDS_MAXIMUM" in result["_validation_flags"]

    def test_ei_exceeds_maximum(self):
        fields = {"14": 55000.0, "16": 3000.0, "18": 2000.0, "22": 7000.0}
        result = _validate_fields(fields, 2024)
        assert "EI_EXCEEDS_MAXIMUM" in result["_validation_flags"]

    def test_tax_rate_anomaly(self):
        fields = {"14": 55000.0, "16": 3000.0, "18": 900.0, "22": 50000.0}
        result = _validate_fields(fields, 2024)
        assert "TAX_RATE_ANOMALY" in result["_validation_flags"]

    def test_confidence_decreases_with_flags(self):
        fields = {"14": 55000.0, "16": 5000.0, "18": 2000.0, "22": 50000.0}
        result = _validate_fields(fields, 2024)
        assert result["_confidence"] < 1.0
        assert len(result["_validation_flags"]) >= 2
