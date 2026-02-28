"""
Pydantic schema for T4 slip — all box numbers 14–67, employer_name, province_code, tax_year, confidence.
"""
from typing import Optional
from pydantic import BaseModel, Field

# T4 box numbers 14 through 67 (common monetary/identifier boxes)
T4_BOX_NUMBERS = [str(i) for i in range(14, 68)]

# CRA-defined descriptions for each T4 box number
T4_BOX_LABELS: dict[str, str] = {
    "14": "Employment income",
    "15": "Special payments",
    "16": "Employee's CPP contributions",
    "16A": "Employee's second CPP contributions (CPP2)",
    "17": "Employee's QPP contributions",
    "17A": "Employee's second QPP contributions (QPP2)",
    "18": "Employee's EI premiums",
    "19": "Employee's EI premiums (Quebec)",
    "20": "RPP contributions",
    "22": "Income tax deducted",
    "24": "EI insurable earnings",
    "26": "CPP/QPP pensionable earnings",
    "28": "Exempt (CPP/QPP, EI, PPIP)",
    "29": "Employment code",
    "30": "Board and lodging",
    "31": "Special work site",
    "32": "Travel in a prescribed zone",
    "33": "Medical travel assistance",
    "34": "Personal use of employer's automobile",
    "36": "Interest-free and low-interest loans",
    "37": "Security options deduction (110(1)(d))",
    "38": "Security options benefits",
    "39": "Security options deduction (110(1)(d.1))",
    "40": "Other taxable allowances and benefits",
    "41": "Security options deduction (110(1)(d.01))",
    "42": "Employment commissions",
    "43": "Canadian Forces personnel and police deduction",
    "44": "Union dues",
    "45": "Employer-offered dental benefits",
    "46": "Charitable donations",
    "50": "RPP or DPSP registration number",
    "52": "Pension adjustment",
    "54": "Employer's account number",
    "55": "Employee's PPIP premiums",
    "56": "PPIP insurable earnings",
    "66": "Eligible retiring allowance",
    "67": "Non-eligible retiring allowance",
}


class T4Fields(BaseModel):
    """Structured T4 field values; box numbers in box_values dict, key fields at top level."""
    employer_name: Optional[str] = None
    province_code: Optional[str] = None
    tax_year: Optional[int] = None
    uncertain_fields: list[str] = Field(default_factory=list)
    box_values: dict[str, Optional[float]] = Field(default_factory=dict)  # "14" -> 85000.00, etc.
    confidence: Optional[float] = None

    class Config:
        extra = "allow"

    @property
    def box_labels(self) -> dict[str, str]:
        """Return CRA-defined labels for all populated box values."""
        return {k: T4_BOX_LABELS.get(k, f"Box {k}") for k in self.box_values if self.box_values[k] is not None}

    def get(self, box: str | int, default: float = 0.0) -> float:
        """Get box value as float."""
        k = str(box)
        v = self.box_values.get(k)
        return float(v) if v is not None else default


def t4_from_dict(data: dict) -> T4Fields:
    """Build T4Fields from raw dict (e.g. from OCR); normalize keys to strings."""
    box_values = {}
    employer_name = data.get("employer_name")
    province_code = data.get("province_code")
    tax_year = data.get("tax_year")
    uncertain_fields = data.get("uncertain_fields", [])
    for k, v in data.items():
        if k in ("employer_name", "province_code", "tax_year", "uncertain_fields", "_validation_flags", "_confidence"):
            continue
        if isinstance(k, int) or (isinstance(k, str) and k.isdigit()):
            box_values[str(k)] = float(v) if v is not None and v != "" else None
    return T4Fields(
        employer_name=employer_name,
        province_code=province_code,
        tax_year=tax_year,
        uncertain_fields=uncertain_fields,
        box_values=box_values,
        confidence=data.get("_confidence"),
    )
