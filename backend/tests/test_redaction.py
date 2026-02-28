"""
Phase 4 verification: SIN, postal code, DOB, name redacted; financial figures preserved.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.redaction_service import redact_pii


def test_sin():
    t = "SIN 123 456 789 and 987-654-321"
    r = redact_pii(t)
    assert "[SIN-REDACTED]" in r
    assert "123" not in r or "123" in "[SIN-REDACTED]"


def test_postal():
    t = "Address: 120 Elm St, Toronto ON M5V 1A1"
    r = redact_pii(t)
    assert "[POSTAL-REDACTED]" in r


def test_dob():
    t = "DOB: 1985-03-12"
    r = redact_pii(t)
    assert "[DOB-REDACTED]" in r


def test_dict_financial_preserved():
    d = {"14": 85000.0, "16": 3867.50, "employer_name": "Acme Corp", "name": "John Doe"}
    r = redact_pii(d)
    assert r.get("14") == 85000.0
    assert r.get("16") == 3867.50
    assert r.get("employer_name") == "Acme Corp"
    assert "name" not in r  # PII key removed


if __name__ == "__main__":
    test_sin()
    test_postal()
    test_dob()
    test_dict_financial_preserved()
    print("Redaction tests passed.")
